"""Agente de tendencias del día + notas de publicidad orgánica (perfil).

Fuente primaria: artículos frescos en DB (scout/RSS).
Complemento: búsqueda multi-motor por temas del perfil (no scrapes site: redes).
Sintetiza CTAs orgánicos para LinkedIn / IG / FB / TikTok / YouTube.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.editorial import NewsArticle
from app.models.profile import ProfessionalProfile
from app.services.ai_gateway import AIGatewayService
from app.services.news_freshness import (
    DEFAULT_MAX_AGE_HOURS,
    effective_publish_at,
    is_stale,
    parse_result_date,
    utc_now_naive,
)
from app.services.news_search_providers import configured_providers, search_news
from app.services.quota import get_active_profile

logger = logging.getLogger(__name__)

PLATFORMS: list[dict[str, str]] = [
    {"id": "linkedin", "label": "LinkedIn"},
    {"id": "youtube", "label": "YouTube"},
    {"id": "x", "label": "X / Twitter"},
    {"id": "tiktok", "label": "TikTok"},
    {"id": "instagram", "label": "Instagram"},
]

_PLATFORM_HOST_HINTS: dict[str, tuple[str, ...]] = {
    "linkedin": ("linkedin.com",),
    "youtube": ("youtube.com", "youtu.be"),
    "x": ("twitter.com", "x.com"),
    "tiktok": ("tiktok.com",),
    "instagram": ("instagram.com",),
}

# Rotación suave de plataforma sugerida para cards (contenido web → canal de distribución)
_DISTRIBUTION_ROTATION = ("linkedin", "youtube", "x", "instagram", "tiktok")

SOCIAL_NOTE_PLATFORMS = ("linkedin", "instagram", "facebook", "tiktok", "youtube")

_PLATFORM_PLAYBOOK: dict[str, dict[str, str]] = {
    "linkedin": {
        "format": "Post profesional + imagen 1:1",
        "ratio": "1:1",
        "where": "Cierre (últimas 2 líneas) + primer comentario con enlace a la fuente",
        "avoid": "Pitch en la primera línea; claims de ROI sin evidencia",
    },
    "instagram": {
        "format": "Carrusel 4:5 (portada + 3 hallazgos + CTA)",
        "ratio": "4:5",
        "where": "Caption (últimas líneas) y sticker de enlace / stories",
        "avoid": "Muro de texto; emojis vacíos sin sustancia",
    },
    "facebook": {
        "format": "Post explicativo + imagen horizontal",
        "ratio": "1.91:1",
        "where": "Cierre del post + primer comentario con enlace",
        "avoid": "Clickbait; posts solo promocionales sin contexto",
    },
    "tiktok": {
        "format": "Video 30–45s / 9:16 con texto en pantalla",
        "ratio": "9:16",
        "where": "Hook 0–3s; CTA verbal al cierre + texto en pantalla",
        "avoid": "Jerga legal densa; vender en el primer segundo",
    },
    "youtube": {
        "format": "Short o microanálisis 3–5 min + thumbnail",
        "ratio": "16:9",
        "where": "Segundos 3–8 (gancho), descripción (CTA) y comentario fijado",
        "avoid": "Mid-roll agresivo; promesas de resultados garantizados",
    },
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


def build_theme_news_queries(
    themes: list[str],
    *,
    max_queries: int = 12,
) -> list[dict[str, str]]:
    """Queries de noticias del día por tema (sin site: redes sociales)."""
    queries: list[dict[str, str]] = []
    seen: set[str] = set()
    theme_cycle = themes or ["inteligencia artificial gobernanza regulación"]
    year = str(utc_now_naive().year)
    for theme in theme_cycle:
        for suffix in ("noticia", "regulación", "México"):
            q = f"{theme} {suffix} {year}".strip()
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            queries.append(
                {
                    "platform": "web",
                    "theme": theme,
                    "query": q,
                }
            )
            if len(queries) >= max_queries:
                return queries
    return queries


# Compat: imports externos / tests
def build_social_queries(
    themes: list[str],
    *,
    max_queries: int = 12,
) -> list[dict[str, str]]:
    return build_theme_news_queries(themes, max_queries=max_queries)


def _guess_platform(url: str, default: str = "web") -> str:
    host = (urlparse(url).netloc or "").lower().lstrip("www.")
    for plat_id, hints in _PLATFORM_HOST_HINTS.items():
        if any(h in host for h in hints):
            return plat_id
    return default


def _suggest_distribution_platform(index: int, url: str = "") -> str:
    guessed = _guess_platform(url, "")
    if guessed:
        return guessed
    return _DISTRIBUTION_ROTATION[index % len(_DISTRIBUTION_ROTATION)]


def hits_from_day_articles(
    db: Session,
    *,
    organization_id: int | None = None,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    limit: int = 40,
    themes: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convierte artículos frescos de la DB en evidencia de tendencias."""
    now = utc_now_naive()
    cutoff = now - timedelta(hours=max(6, int(max_age_hours)))
    q = db.query(NewsArticle).filter(NewsArticle.published_at.isnot(None))
    if organization_id is not None:
        q = q.filter(NewsArticle.organization_id == organization_id)
    # Preferir published_at reciente
    try:
        rows = (
            q.filter(NewsArticle.published_at >= cutoff)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit * 2)
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("hits_from_day_articles query failed: %s", exc)
        rows = []

    theme_hint = (themes or [""])[0] if themes else ""
    hits: list[dict[str, Any]] = []
    for i, art in enumerate(rows):
        published = effective_publish_at(art) or art.published_at
        if not published or is_stale(published, max_age_hours=max_age_hours, now=now):
            continue
        url = (art.source_url or "").strip()
        title = (art.title or "").strip()
        if not url or not title:
            continue
        clf = art.classification_json if isinstance(art.classification_json, dict) else {}
        scout = clf.get("scout") if isinstance(clf.get("scout"), dict) else {}
        theme = (
            scout.get("news_type_name")
            or scout.get("news_type_slug")
            or theme_hint
            or "Actualidad"
        )
        snippet = (art.excerpt or (art.full_text or "")[:280] or "").strip()
        hits.append(
            {
                "platform": _suggest_distribution_platform(i, url),
                "theme": str(theme)[:120],
                "title": title[:280],
                "url": url[:1024],
                "snippet": snippet[:400],
                "query": "db:day_articles",
                "detected_at": published.isoformat() + "Z",
                "source": "db_article",
                "article_id": art.id,
            }
        )
        if len(hits) >= limit:
            break
    return hits


def research_theme_news(
    queries: list[dict[str, str]],
    *,
    max_results_per_query: int = 3,
    max_hits: int = 40,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
) -> list[dict[str, Any]]:
    """Busca noticias por tema con failover multi-motor; exige fecha ≤ max_age."""
    hits: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    now = utc_now_naive()

    for item in queries:
        query = item["query"]
        theme = item.get("theme") or ""
        platform = item.get("platform") or "web"
        results = search_news(
            query,
            max_results=max_results_per_query,
            timelimit="d",
            prefer_fresh_days=1,
        )
        if len(results) < max(1, max_results_per_query // 2):
            more = search_news(
                query,
                max_results=max_results_per_query,
                timelimit="w",
                prefer_fresh_days=7,
            )
            seen = {(r.get("url") or "").split("?")[0].lower() for r in results}
            for row in more:
                key = (row.get("url") or "").split("?")[0].lower()
                if key and key not in seen:
                    results.append(row)
                    seen.add(key)

        for r in results:
            url = (r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            snippet = (r.get("body") or "").strip()
            if not url or not title:
                continue
            published = parse_result_date(r.get("date"))
            if not published:
                from app.services.news_freshness import extract_explicit_publish_date

                published = extract_explicit_publish_date(f"{title}\n{snippet}")
            if not published:
                continue
            if is_stale(published, max_age_hours=max_age_hours, now=now):
                continue
            cited_years = [int(y) for y in re.findall(r"\b(20[0-2]\d)\b", title)]
            if cited_years and all(y < now.year for y in cited_years):
                continue
            url_key = url.split("?")[0].lower()
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            hits.append(
                {
                    "platform": _suggest_distribution_platform(len(hits), url)
                    if platform == "web"
                    else _guess_platform(url, platform),
                    "theme": theme,
                    "title": title[:280],
                    "url": url[:1024],
                    "snippet": snippet[:400],
                    "query": query,
                    "detected_at": published.isoformat() + "Z",
                    "source": r.get("provider") or "news_search",
                }
            )
            if len(hits) >= max_hits:
                return hits

    return hits


def research_social_trends(
    queries: list[dict[str, str]],
    *,
    max_results_per_query: int = 3,
    max_hits: int = 40,
) -> list[dict[str, Any]]:
    """Compat: ahora investiga noticias por tema, no scrapes de redes."""
    return research_theme_news(
        queries,
        max_results_per_query=max_results_per_query,
        max_hits=max_hits,
    )


def _signal_pool(
    trends: list[dict[str, Any]],
    hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pool: list[dict[str, Any]] = []
    for t in trends:
        if not isinstance(t, dict):
            continue
        urls = t.get("urls") if isinstance(t.get("urls"), list) else []
        pool.append(
            {
                "title": (t.get("summary") or t.get("theme") or "").strip(),
                "theme": (t.get("theme") or "").strip(),
                "url": (urls[0] if urls else "") or "",
                "detected_at": t.get("detected_at"),
                "urgency": t.get("urgency"),
                "market": t.get("market"),
            }
        )
    if pool:
        return pool
    for h in hits:
        if not isinstance(h, dict) or not h.get("detected_at"):
            continue
        pool.append(
            {
                "title": (h.get("title") or "").strip(),
                "theme": (h.get("theme") or "").strip(),
                "url": (h.get("url") or "").strip(),
                "detected_at": h.get("detected_at"),
                "urgency": "Media",
                "market": None,
            }
        )
    return pool


def _truncate(text: str, n: int) -> str:
    t = " ".join((text or "").split())
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def build_structured_ad_notes(
    profile: ProfessionalProfile,
    *,
    trends: list[dict[str, Any]] | None = None,
    hits: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Notas accionables por red: gancho, copy listo, CTA, dónde/evitar + prompt de imagen."""
    services = _service_names(profile)
    service = services[0] if services else "una sesión de diagnóstico"
    audiences = _audience_labels(profile)
    audience = audiences[0] if audiences else "general counsel y líderes legales"
    author = (profile.full_name or "Juan Vásquez").strip()
    pool = _signal_pool(trends or [], hits or [])

    notes: list[dict[str, Any]] = []
    for i, platform in enumerate(SOCIAL_NOTE_PLATFORMS):
        play = _PLATFORM_PLAYBOOK[platform]
        signal = pool[i % len(pool)] if pool else None
        news_title = _truncate((signal or {}).get("title") or "Señal del día en IA / regulación", 140)
        theme = (signal or {}).get("theme") or "IA y gobernanza"
        news_url = (signal or {}).get("url") or ""
        urgency = (signal or {}).get("urgency") or "Media"
        market = (signal or {}).get("market") or "México / Latam"

        if platform == "linkedin":
            hook = f"Señal del día para {audience}: {news_title}"
            post = (
                f"{hook}\n\n"
                f"Por qué importa hoy: impacta decisiones de {audience} en {market}.\n"
                f"Ángulo: {theme} · urgencia {urgency}.\n\n"
                f"Pregunta: ¿tu equipo ya tiene criterio documentado ante esto?\n\n"
                f"— {author}"
            )
            cta = f"Si te sirve profundizar, agendemos {service}."
        elif platform == "instagram":
            hook = _truncate(news_title, 70)
            post = (
                f"Portada: {hook}\n"
                f"Slide 2: Qué pasó (1 dato).\n"
                f"Slide 3: Riesgo para {audience}.\n"
                f"Slide 4: 1 acción esta semana.\n"
                f"Slide 5: CTA → {service}."
            )
            cta = f"Guarda este carrusel y escríbeme «IA» para {service}."
        elif platform == "facebook":
            hook = f"Hoy en {market}: {news_title}"
            post = (
                f"{hook}\n\n"
                f"Resumen en lenguaje claro para no-especialistas.\n"
                f"Tema: {theme}.\n\n"
                f"Al final: qué debería preguntar un GC mañana."
            )
            cta = f"Comenta «quiero el checklist» o agenda {service}."
        elif platform == "tiktok":
            hook = f"En 3 segundos: { _truncate(news_title, 55) }"
            post = (
                f"0–3s: {hook}\n"
                f"3–20s: qué implica para empresas en {market}.\n"
                f"20–40s: 1 error típico + 1 acción.\n"
                f"Cierre: pregunta + CTA a {service}."
            )
            cta = "Sígueme para señales legales de IA sin humo."
        else:  # youtube
            hook = f"Microanálisis: { _truncate(news_title, 80) }"
            post = (
                f"Título: {hook}\n"
                f"Estructura: contexto (30s) → riesgo GC (90s) → qué hacer esta semana (60s).\n"
                f"Descripción: enlace a fuente + CTA a {service}."
            )
            cta = f"Comentario fijado: agenda {service}."

        from app.services.social_creative_service import build_social_hero_prompt

        image_prompt = build_social_hero_prompt(
            platform=platform,
            news_title=news_title,
            theme=theme,
            market=market,
            hook=hook,
        )

        notes.append(
            {
                "platform": platform,
                "format": play["format"],
                "hook": hook,
                "post": post,
                "cta": cta,
                "where": play["where"],
                "avoid": play["avoid"],
                "how": f"{play['format']}. {cta}",
                "theme": theme,
                "news_title": news_title,
                "news_url": news_url,
                "urgency": urgency,
                "market": market,
                "image_prompt": image_prompt,
                "image_ratio": play["ratio"],
            }
        )
    return notes


def _normalize_ad_notes_list(
    raw: list[Any],
    profile: ProfessionalProfile,
    *,
    trends: list[dict[str, Any]],
    hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Asegura 5 plataformas con campos estructurados (rellena con playbook si el LLM vino pobre)."""
    structured = {
        n["platform"]: n
        for n in build_structured_ad_notes(profile, trends=trends, hits=hits)
    }
    by_plat: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        plat = str(item.get("platform") or "").lower().strip()
        if plat not in structured:
            continue
        base = structured[plat]
        merged = {**base, **{k: v for k, v in item.items() if v not in (None, "", [])}}
        # Si el LLM solo mandó where/how genéricos, preservar copy estructurado
        if not merged.get("post") or len(str(merged.get("post") or "")) < 40:
            merged["post"] = base["post"]
        if not merged.get("hook"):
            merged["hook"] = base["hook"]
        if not merged.get("cta"):
            merged["cta"] = base["cta"]
        by_plat[plat] = merged
    return [by_plat.get(p) or structured[p] for p in SOCIAL_NOTE_PLATFORMS]


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
    trends: list[dict[str, Any]] = []
    for h in hits[:8]:
        if not h.get("detected_at"):
            continue
        trends.append(
            {
                "theme": h.get("theme") or "",
                "platform": h.get("platform") or "web",
                "summary": h.get("title") or "",
                "urls": [h["url"]] if h.get("url") else [],
                "detected_at": h.get("detected_at"),
                "growth_pct": None,
                "urgency": "Media",
                "market": "México" if "méxico" in (h.get("query") or "").lower() else None,
            }
        )
    sparse = len(trends) == 0
    if sparse:
        logger.info(
            "trend_ad_advisor fallback: 0 hits frescos — tips estáticos sin fingir tendencias"
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

    ad_notes = build_structured_ad_notes(profile, trends=trends, hits=hits)

    return {
        "generated_at": _utcnow_iso(),
        "kind": "organic_social_ad_notes",
        "disclaimer": (
            "Sugerencias editoriales orgánicas para tus redes. "
            "No incluyen compra ni gestión de anuncios pagados."
            + (
                " Hoy no hubo señales datadas en inventario/motores; solo tips de publicación."
                if sparse
                else ""
            )
        ),
        "trends": trends,
        "formats_working": formats,
        "ad_notes": ad_notes,
        "meta": {
            "queries_run": [q["query"] for q in queries],
            "platforms": [p["id"] for p in PLATFORMS],
            "hits_count": len(hits),
            "fresh_hits": len(trends),
            "source": "fallback",
            "providers": configured_providers(),
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
            "detected_at": h.get("detected_at"),
            "source": h.get("source"),
        }
        for h in hits[:28]
        if h.get("detected_at")
    ]

    today = _utcnow_iso()[:10]
    prompt = f"""Eres el advisor de tendencias y publicidad ORGÁNICA de Autoridad 360 (voz Juan Vásquez:
profesional, soberana, sin hype). Analiza hallazgos REALES del día {today} y produce SOLO JSON válido.

PERFIL:
- Nombre: {profile.full_name}
- Título: {profile.title or ""}
- Pilares: {json.dumps(pillars, ensure_ascii=False)}
- Temas activos: {json.dumps(themes, ensure_ascii=False)}
- Audiencias: {json.dumps(audiences, ensure_ascii=False)}
- Servicios (para CTAs suaves): {json.dumps(services, ensure_ascii=False)}

HALLAZGOS (noticias del día en DB o motores; NO inventes URLs ni fechas):
{json.dumps(evidence, ensure_ascii=False)}

Devuelve exactamente este JSON:
{{
  "trends": [
    {{
      "theme": "tema del perfil",
      "platform": "linkedin|youtube|x|tiktok|instagram|web",
      "summary": "qué está resonando HOY (1-2 frases)",
      "urls": ["url real de evidence o []"],
      "detected_at": "ISO8601 de evidence",
      "growth_pct": null,
      "urgency": "Alta|Media|null",
      "market": "Latam|EE. UU.|México|null"
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
      "format": "Post + imagen 1:1",
      "hook": "primera línea con la noticia del día",
      "post": "copy listo para publicar (3-6 líneas) atado a un hallazgo real",
      "cta": "CTA suave a un servicio del perfil",
      "where": "dónde insertar el CTA",
      "avoid": "qué evitar",
      "news_title": "título real de evidence",
      "news_url": "url real o vacío",
      "image_prompt": "fondo visual sin texto para la noticia"
    }}
  ]
}}

Reglas:
- Solo trends con detected_at de las últimas 36 h (usa el de evidence). Si evidence está vacío, trends=[].
- 0 a 6 trends; usa solo URLs que aparezcan en HALLAZGOS. Nunca inventes noticias viejas.
- growth_pct: null salvo que evidence cite un % real; no inventes cifras.
- Urgencia Alta solo si hay ≥2 URLs distintas sobre el mismo tema en evidence.
- ad_notes OBLIGATORIAS: linkedin, instagram, facebook, tiktok, youtube.
- Cada ad_note debe anclarse a una noticia distinta de evidence (rota señales).
- post = texto listo para copiar/pegar, no consejos genéricos.
- Enfoque 100% orgánico. Cero Meta Ads / LinkedIn Ads pagados.
- Tono Juan: claro, útil para GC/legal; sin emojis ni hype.
"""

    try:
        gateway = AIGatewayService(db)
        res = gateway.generate_text(
            prompt=prompt,
            system_prompt=(
                "Advisor de tendencias del DÍA. Solo evidencia datada. Devuelve SOLO JSON válido."
            ),
        )
        raw = res.get("text") or ""
        data = _extract_json_blob(raw)
        if not data:
            return None
        trends = data.get("trends") if isinstance(data.get("trends"), list) else []
        evidence_urls = {
            (e.get("url") or "").split("?")[0].lower() for e in evidence if e.get("url")
        }
        cleaned_trends: list[dict[str, Any]] = []
        for t in trends:
            if not isinstance(t, dict):
                continue
            urls = t.get("urls") if isinstance(t.get("urls"), list) else []
            url0 = (urls[0] if urls else "") or ""
            url_key = url0.split("?")[0].lower()
            if evidence_urls and url_key and url_key not in evidence_urls:
                continue
            if not t.get("detected_at"):
                match = next(
                    (
                        e
                        for e in evidence
                        if (e.get("url") or "").split("?")[0].lower() == url_key
                    ),
                    None,
                )
                if match and match.get("detected_at"):
                    t["detected_at"] = match["detected_at"]
                else:
                    continue
            # No confiar en growth inventado
            if t.get("growth_pct") is not None and not isinstance(t.get("growth_pct"), (int, float)):
                t["growth_pct"] = None
            cleaned_trends.append(t)
        trends = cleaned_trends
        ad_notes = data.get("ad_notes") if isinstance(data.get("ad_notes"), list) else []
        ad_notes = _normalize_ad_notes_list(
            ad_notes, profile, trends=trends, hits=hits
        )
        formats = (
            data.get("formats_working")
            if isinstance(data.get("formats_working"), list)
            else []
        )
        if not formats:
            formats = [
                {"format": n.get("format"), "why": n.get("cta"), "platform": n.get("platform")}
                for n in ad_notes[:3]
            ]

        return {
            "generated_at": _utcnow_iso(),
            "kind": "organic_social_ad_notes",
            "disclaimer": (
                "Sugerencias editoriales orgánicas para tus redes. "
                "No incluyen compra ni gestión de anuncios pagados."
                + (
                    " Sin señales datadas del día en esta corrida."
                    if not trends
                    else ""
                )
            ),
            "trends": trends[:6],
            "formats_working": formats[:6],
            "ad_notes": ad_notes,
            "meta": {
                "queries_run": [q["query"] for q in queries],
                "platforms": [p["id"] for p in PLATFORMS],
                "hits_count": len(hits),
                "fresh_hits": len(evidence),
                "source": "llm",
                "providers": configured_providers(),
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
    """Arma tendencias del día desde DB + motores; guarda notas en el perfil."""
    profile = get_active_profile(db, slug=slug, organization_id=organization_id)
    if not profile:
        raise ValueError("Profile not found")

    themes = _theme_labels(profile)
    org_id = organization_id if organization_id is not None else getattr(profile, "organization_id", None)

    db_hits = hits_from_day_articles(
        db,
        organization_id=org_id,
        max_age_hours=DEFAULT_MAX_AGE_HOURS,
        limit=32,
        themes=themes,
    )

    queries = build_theme_news_queries(themes, max_queries=max_queries)
    search_hits: list[dict[str, Any]] = []
    # Complementar si el inventario del día es fino
    if len(db_hits) < 8:
        search_hits = research_theme_news(
            queries,
            max_results_per_query=max_results_per_query,
            max_hits=40,
        )

    seen: set[str] = set()
    hits: list[dict[str, Any]] = []
    for h in db_hits + search_hits:
        key = (h.get("url") or "").split("?")[0].lower()
        if not key or key in seen:
            continue
        seen.add(key)
        hits.append(h)

    notes = _synthesize_with_llm(db, profile, hits, queries)
    if not notes:
        notes = _fallback_notes(profile, hits, queries)

    # Garantizar estructura rica aunque el LLM haya venido pobre
    notes["ad_notes"] = _normalize_ad_notes_list(
        notes.get("ad_notes") if isinstance(notes.get("ad_notes"), list) else [],
        profile,
        trends=notes.get("trends") if isinstance(notes.get("trends"), list) else [],
        hits=hits,
    )

    # Imágenes: no auto-generar; la UI pide "Crear imagen" por plataforma.
    for note in notes.get("ad_notes") or []:
        if isinstance(note, dict):
            note.pop("image_url", None)
            note.pop("image_engine", None)

    # Enriquecer meta con origen
    meta = notes.get("meta") if isinstance(notes.get("meta"), dict) else {}
    meta["db_hits"] = len(db_hits)
    meta["search_hits"] = len(search_hits)
    meta["providers"] = configured_providers()
    meta["images_on_demand"] = True
    notes["meta"] = meta

    if persist:
        profile.ad_trend_notes_json = notes
        db.commit()
        db.refresh(profile)

    return notes


def generate_ad_note_image(
    db: Session,
    *,
    platform: str,
    organization_id: int | None = None,
    slug: str = "juan-vasquez",
    use_openai: bool = True,
) -> dict[str, Any]:
    """Genera (o regenera) la imagen de una sola plataforma en ad_notes guardadas."""
    from app.services.social_creative_service import enrich_ad_notes_with_images

    profile = get_active_profile(db, slug=slug, organization_id=organization_id)
    if not profile:
        raise ValueError("Profile not found")
    notes = getattr(profile, "ad_trend_notes_json", None)
    if not isinstance(notes, dict):
        raise ValueError("No hay notas del día. Genera primero las notas de tendencias.")

    plat = (platform or "").strip().lower()
    if plat == "twitter":
        plat = "x"
    ad_notes = notes.get("ad_notes") if isinstance(notes.get("ad_notes"), list) else []
    target = next(
        (
            n
            for n in ad_notes
            if isinstance(n, dict) and str(n.get("platform") or "").lower() == plat
        ),
        None,
    )
    if not target:
        raise ValueError(f"No hay nota para la plataforma «{platform}».")

    # Limpiar imagen previa de esta plataforma para forzar regeneración
    target.pop("image_url", None)
    target.pop("image_engine", None)

    partial = {**notes, "ad_notes": [target]}
    org_id = organization_id if organization_id is not None else getattr(profile, "organization_id", None)
    enriched = enrich_ad_notes_with_images(
        db,
        partial,
        organization_id=org_id,
        use_openai=use_openai,
        max_openai=1 if use_openai else 0,
    )
    new_note = (enriched.get("ad_notes") or [target])[0]
    updated = []
    for n in ad_notes:
        if isinstance(n, dict) and str(n.get("platform") or "").lower() == plat:
            updated.append(new_note)
        else:
            updated.append(n)
    notes = {**notes, "ad_notes": updated}
    meta = notes.get("meta") if isinstance(notes.get("meta"), dict) else {}
    meta["last_image_platform"] = plat
    meta["last_image_at"] = _utcnow_iso()
    notes["meta"] = meta
    profile.ad_trend_notes_json = notes
    db.commit()
    db.refresh(profile)
    return {"notes": notes, "note": new_note, "platform": plat}


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
