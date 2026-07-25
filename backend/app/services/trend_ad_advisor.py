"""Agente de tendencias sociales + notas de publicidad orgánica (perfil).

Investiga redes (LinkedIn, YouTube, X, TikTok, Instagram) vía DuckDuckGo
con filtros por sitio según temas del perfil, y sintetiza notas accionables
de dónde/cómo insertar CTAs orgánicos (sin compra de ads).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from ddgs import DDGS
from sqlalchemy.orm import Session

from app.models.profile import ProfessionalProfile
from app.services.ai_gateway import AIGatewayService
from app.services.quota import get_active_profile

logger = logging.getLogger(__name__)

PLATFORMS: list[dict[str, str]] = [
    {
        "id": "linkedin",
        "label": "LinkedIn",
        "site": "site:linkedin.com/posts OR site:linkedin.com/pulse",
    },
    {
        "id": "youtube",
        "label": "YouTube",
        "site": "site:youtube.com",
    },
    {
        "id": "x",
        "label": "X / Twitter",
        "site": "site:twitter.com OR site:x.com",
    },
    {
        "id": "tiktok",
        "label": "TikTok",
        "site": "site:tiktok.com",
    },
    {
        "id": "instagram",
        "label": "Instagram",
        "site": "site:instagram.com",
    },
]

_PLATFORM_HOST_HINTS: dict[str, tuple[str, ...]] = {
    "linkedin": ("linkedin.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "x": ("twitter.com", "x.com"),
    "tiktok": ("tiktok.com",),
    "instagram": ("instagram.com",),
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _theme_labels(profile: ProfessionalProfile, *, max_themes: int = 6) -> list[str]:
    themes = profile.search_themes_json or []
    labels: list[str] = []
    for t in themes:
        if not isinstance(t, dict):
            continue
        if t.get("active") is False:
            continue
        name = (t.get("name") or t.get("query") or t.get("slug") or "").strip()
        if name and name.lower() not in {x.lower() for x in labels}:
            labels.append(name)
        if len(labels) >= max_themes:
            break
    if not labels:
        for p in profile.pillars or []:
            if getattr(p, "is_active", True) and p.name:
                labels.append(p.name.strip())
            if len(labels) >= max_themes:
                break
    return labels[:max_themes]


def _service_names(profile: ProfessionalProfile) -> list[str]:
    services = profile.services_json or []
    out: list[str] = []
    for s in services:
        if isinstance(s, str) and s.strip():
            out.append(s.strip())
        elif isinstance(s, dict):
            name = (s.get("name") or s.get("title") or "").strip()
            if name:
                out.append(name)
    return out[:8]


def _audience_labels(profile: ProfessionalProfile) -> list[str]:
    audiences = profile.audiences_json or []
    out: list[str] = []
    for a in audiences:
        if isinstance(a, str) and a.strip():
            out.append(a.strip())
        elif isinstance(a, dict):
            name = (a.get("name") or a.get("label") or "").strip()
            if name:
                out.append(name)
    return out[:6]


def build_social_queries(
    themes: list[str],
    *,
    max_queries: int = 12,
) -> list[dict[str, str]]:
    """Construye queries con site filters: plataformas × temas (cap)."""
    queries: list[dict[str, str]] = []
    seen: set[str] = set()
    # Round-robin: primero un query por plataforma con el tema top, luego combos
    theme_cycle = themes or ["inteligencia artificial gobernanza"]
    for theme in theme_cycle:
        for plat in PLATFORMS:
            q = f'{plat["site"]} {theme}'
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append({"platform": plat["id"], "theme": theme, "query": q})
            if len(queries) >= max_queries:
                return queries
    # Variante “tendencia / 2026” para YouTube y LinkedIn con temas top
    for theme in theme_cycle[:3]:
        for plat_id, extra in (
            ("youtube", f"site:youtube.com {theme} tendencia 2026"),
            ("linkedin", f"site:linkedin.com {theme} IA"),
        ):
            key = extra.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append({"platform": plat_id, "theme": theme, "query": extra})
            if len(queries) >= max_queries:
                return queries
    return queries


def _guess_platform(url: str, default: str) -> str:
    host = (urlparse(url).netloc or "").lower().lstrip("www.")
    for plat_id, hints in _PLATFORM_HOST_HINTS.items():
        if any(h in host for h in hints):
            return plat_id
    return default


def research_social_trends(
    queries: list[dict[str, str]],
    *,
    max_results_per_query: int = 3,
    max_hits: int = 40,
) -> list[dict[str, Any]]:
    """Busca en DDGS text (+ news) y deduplica por URL."""
    hits: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    try:
        ddgs = DDGS()
    except Exception as exc:  # noqa: BLE001
        logger.warning("DDGS init failed: %s", exc)
        return []

    for item in queries:
        query = item["query"]
        platform = item["platform"]
        theme = item.get("theme") or ""
        try:
            results = list(ddgs.text(query, max_results=max_results_per_query))
        except Exception as exc:  # noqa: BLE001
            logger.warning("DDGS text failed for %s: %s", query[:80], exc)
            results = []

        # Complemento news solo para LinkedIn/YouTube (más útiles)
        if platform in ("linkedin", "youtube") and len(results) < max_results_per_query:
            try:
                news = list(ddgs.news(f"{theme} {platform}", max_results=2))
                results.extend(news)
            except Exception:  # noqa: BLE001
                pass

        for r in results:
            url = (r.get("href") or r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            snippet = (r.get("body") or r.get("snippet") or "").strip()
            if not url or not title:
                continue
            url_key = url.split("?")[0].lower()
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            hits.append(
                {
                    "platform": _guess_platform(url, platform),
                    "theme": theme,
                    "title": title[:280],
                    "url": url[:1024],
                    "snippet": snippet[:400],
                    "query": query,
                }
            )
            if len(hits) >= max_hits:
                return hits

    return hits


def _extract_json_blob(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        # Intento suave: quitar trailing commas
        cleaned = re.sub(r",\s*}", "}", text[start:end])
        cleaned = re.sub(r",\s*]", "]", cleaned)
        try:
            data = json.loads(cleaned)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _fallback_notes(
    profile: ProfessionalProfile,
    hits: list[dict[str, Any]],
    queries: list[dict[str, str]],
) -> dict[str, Any]:
    services = _service_names(profile)
    primary_service = services[0] if services else "asesoría en gobernanza de IA"
    trends: list[dict[str, Any]] = []
    for h in hits[:6]:
        trends.append(
            {
                "theme": h.get("theme") or "",
                "platform": h.get("platform") or "",
                "summary": h.get("title") or "",
                "urls": [h["url"]] if h.get("url") else [],
            }
        )
    if not trends:
        for theme in _theme_labels(profile)[:4]:
            trends.append(
                {
                    "theme": theme,
                    "platform": "linkedin",
                    "summary": f"Monitorear conversación sobre «{theme}» en redes (sin hits web en esta corrida).",
                    "urls": [],
                }
            )

    formats = [
        {
            "format": "carrusel checklist",
            "why": "Fácil de escanear para GCs; cierra con CTA a servicio.",
            "platform": "linkedin",
        },
        {
            "format": "video corto explicativo",
            "why": "Hook de 3s + un riesgo concreto + CTA en descripción.",
            "platform": "youtube",
        },
        {
            "format": "hilo o post corto de riesgo",
            "why": "Una pregunta que el GC debería hacer; CTA suave al final.",
            "platform": "x",
        },
    ]

    cta_by_platform = {
        "linkedin": {
            "where": "Cierre del post (últimas 2 líneas) y primer comentario con enlace.",
            "how": f"Si estás evaluando {primary_service}, escribe y te paso el checklist que uso con GCs.",
            "avoid": "Pitch de venta en la primera línea; claims de ROI sin evidencia.",
        },
        "youtube": {
            "where": "Segundos 3–8 (gancho), descripción (CTA) y comentario fijado.",
            "how": f"En la descripción: guía gratuita / conversación sobre {primary_service}.",
            "avoid": "Mid-roll agresivo; promesas de resultados garantizados.",
        },
        "x": {
            "where": "Último tweet del hilo o reply propio.",
            "how": f"¿Quieres el marco que uso en {primary_service}? DM abierto.",
            "avoid": "Hilos de 20+ sin valor; hashtags spam.",
        },
        "tiktok": {
            "where": "Hook visual 0–3s; CTA verbal al cierre + texto en pantalla.",
            "how": f"Sígueme si lideras cumplimiento/IA; en bio detallo {primary_service}.",
            "avoid": "Jerga legal densa; vender en el primer segundo.",
        },
        "instagram": {
            "where": "Caption (últimas líneas) y sticker de enlace / stories.",
            "how": f"Guarda este carrusel y escríbeme «IA» si quieres revisar {primary_service}.",
            "avoid": "Wall of text; emojis vacíos sin sustancia.",
        },
    }

    return {
        "generated_at": _utcnow_iso(),
        "kind": "organic_social_ad_notes",
        "disclaimer": (
            "Sugerencias editoriales orgánicas para tus redes. "
            "No incluyen compra ni gestión de anuncios pagados."
        ),
        "trends": trends,
        "formats_working": formats,
        "ad_notes": [
            {"platform": pid, **body} for pid, body in cta_by_platform.items()
        ],
        "meta": {
            "queries_run": [q["query"] for q in queries],
            "platforms": [p["id"] for p in PLATFORMS],
            "hits_count": len(hits),
            "source": "fallback",
            "services": services,
            "audiences": _audience_labels(profile),
        },
    }


def _synthesize_with_llm(
    db: Session,
    profile: ProfessionalProfile,
    hits: list[dict[str, Any]],
    queries: list[dict[str, str]],
) -> dict[str, Any] | None:
    themes = _theme_labels(profile)
    services = _service_names(profile)
    audiences = _audience_labels(profile)
    pillars = [
        {"slug": p.slug, "name": p.name}
        for p in (profile.pillars or [])
        if getattr(p, "is_active", True)
    ]

    evidence = [
        {
            "platform": h.get("platform"),
            "theme": h.get("theme"),
            "title": h.get("title"),
            "url": h.get("url"),
            "snippet": (h.get("snippet") or "")[:220],
        }
        for h in hits[:28]
    ]

    prompt = f"""Eres el advisor de tendencias y publicidad ORGÁNICA de Autoridad 360 (voz Juan Vásquez:
profesional, soberana, sin hype). Analiza hallazgos reales de redes y produce SOLO JSON válido.

PERFIL:
- Nombre: {profile.full_name}
- Título: {profile.title or ""}
- Pilares: {json.dumps(pillars, ensure_ascii=False)}
- Temas activos: {json.dumps(themes, ensure_ascii=False)}
- Audiencias: {json.dumps(audiences, ensure_ascii=False)}
- Servicios (para CTAs suaves): {json.dumps(services, ensure_ascii=False)}

HALLAZGOS DE BÚSQUEDA (títulos/URLs reales; NO inventes URLs):
{json.dumps(evidence, ensure_ascii=False)}

Devuelve exactamente este JSON:
{{
  "trends": [
    {{
      "theme": "tema del perfil",
      "platform": "linkedin|youtube|x|tiktok|instagram",
      "summary": "qué está resonando (1-2 frases)",
      "urls": ["url real de evidence o []"]
    }}
  ],
  "formats_working": [
    {{
      "format": "nombre del formato",
      "why": "por qué encaja con el perfil",
      "platform": "linkedin|youtube|x|tiktok|instagram"
    }}
  ],
  "ad_notes": [
    {{
      "platform": "linkedin",
      "where": "dónde insertar el CTA orgánico",
      "how": "texto CTA suave atado a un servicio del perfil",
      "avoid": "qué evitar"
    }}
  ]
}}

Reglas:
- 4 a 6 trends; usa solo URLs que aparezcan en HALLAZGOS.
- ad_notes: una entrada por cada plataforma linkedin, youtube, x, tiktok, instagram.
- Enfoque 100% orgánico (posts/videos propios). Cero ideas de Meta Ads / LinkedIn Ads pagados.
- Tono Juan: claro, útil para GC/legal; sin emojis ni hype.
"""

    try:
        gateway = AIGatewayService(db)
        res = gateway.generate_text(
            prompt=prompt,
            system_prompt="Advisor de tendencias sociales. Devuelve SOLO JSON válido.",
        )
        raw = res.get("text") or ""
        data = _extract_json_blob(raw)
        if not data:
            return None
        # Normalizar mínimamente
        trends = data.get("trends") if isinstance(data.get("trends"), list) else []
        formats = (
            data.get("formats_working")
            if isinstance(data.get("formats_working"), list)
            else []
        )
        ad_notes = data.get("ad_notes") if isinstance(data.get("ad_notes"), list) else []
        # Completar plataformas faltantes en ad_notes
        have = {
            (n.get("platform") or "").lower()
            for n in ad_notes
            if isinstance(n, dict)
        }
        fallback = _fallback_notes(profile, hits, queries)
        for note in fallback["ad_notes"]:
            if note["platform"] not in have:
                ad_notes.append(note)

        return {
            "generated_at": _utcnow_iso(),
            "kind": "organic_social_ad_notes",
            "disclaimer": (
                "Sugerencias editoriales orgánicas para tus redes. "
                "No incluyen compra ni gestión de anuncios pagados."
            ),
            "trends": trends[:6],
            "formats_working": formats[:6],
            "ad_notes": ad_notes[:5],
            "meta": {
                "queries_run": [q["query"] for q in queries],
                "platforms": [p["id"] for p in PLATFORMS],
                "hits_count": len(hits),
                "source": "llm",
                "services": services,
                "audiences": audiences,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM synthesize failed: %s", exc)
        return None


def generate_ad_trend_notes(
    db: Session,
    *,
    organization_id: int | None = None,
    slug: str = "juan-vasquez",
    max_queries: int = 12,
    max_results_per_query: int = 3,
    persist: bool = True,
) -> dict[str, Any]:
    """Investiga redes + sintetiza notas; opcionalmente guarda en el perfil."""
    profile = get_active_profile(db, slug=slug, organization_id=organization_id)
    if not profile:
        raise ValueError("Profile not found")

    themes = _theme_labels(profile)
    queries = build_social_queries(themes, max_queries=max_queries)
    hits = research_social_trends(
        queries,
        max_results_per_query=max_results_per_query,
    )
    notes = _synthesize_with_llm(db, profile, hits, queries)
    if not notes:
        notes = _fallback_notes(profile, hits, queries)

    if persist:
        profile.ad_trend_notes_json = notes
        db.commit()
        db.refresh(profile)

    return notes


def get_stored_ad_trend_notes(
    db: Session,
    *,
    organization_id: int | None = None,
    slug: str = "juan-vasquez",
) -> dict[str, Any] | None:
    profile = get_active_profile(db, slug=slug, organization_id=organization_id)
    if not profile:
        return None
    data = getattr(profile, "ad_trend_notes_json", None)
    return data if isinstance(data, dict) else None
