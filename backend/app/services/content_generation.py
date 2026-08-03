"""Generación multi-formato — solo sobre texto ya verificado en BD."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ContentPackage, ContentPiece, NewsArticle, ProfessionalProfile
from app.services.audit import log_audit
from app.services.content_review import run_reviews
from app.services.llm import _call_model, _extract_json, _prompt_hash, grounding_score
from app.services.quota import get_active_profile
from app.services.prompts.content_prompts import (
    GENERATION_PROMPT,
    LINKEDIN_REWRITE_PROMPT,
    NARRATIVE_ANGLES,
    get_rewrite_prompt,
)

FORMATS = ("linkedin", "video_script", "carousel", "newsletter")
logger = logging.getLogger(__name__)

def language_instruction(code: str) -> str:
    """Instrucción explícita de idioma para el LLM (códigos cortos no bastan)."""
    normalized = (code or "es").strip().lower()
    if normalized in {"en", "en-us", "en_us", "english"}:
        return (
            "English (US). Write ALL titles, body_text, slides and CTAs in English. "
            "Do not write Spanish. Keep proper names and source URLs unchanged."
        )
    return (
        "español mexicano (es-MX). Escribe TODOS los títulos, body_text, slides y CTAs "
        "en español. No escribas en inglés. Conserva nombres propios y URLs de fuente."
    )


def _persona_block_for_article(db: Session, article: NewsArticle) -> str:
    from app.services.juan_persona import get_juan_persona_block

    return get_juan_persona_block(
        db,
        organization_id=getattr(article, "organization_id", None),
        practice="editorial",
    )


def _key_facts(article: NewsArticle) -> list[str]:
    data = article.classification_json or {}
    facts = data.get("key_facts") or []
    return [str(f) for f in facts]


def _draft_linkedin(summary: str, bullets: list[str], cite: str, title: str) -> tuple[str, dict, str]:
    body = (
        f"{summary}\n\n"
        + "\n".join(f"• {b}" for b in bullets[:3])
        + f"\n\n{cite}"
    )
    body_json = {"format": "linkedin", "bullets": bullets[:3]}
    new_title = f"Análisis: {title[:80]}"
    return body, body_json, new_title


def _draft_video_script(summary: str, bullets: list[str], cite: str, title: str) -> tuple[str, dict, str]:
    body = (
        f"HOOK: {title}\n\n"
        f"DESARROLLO:\n{summary}\n\n"
        + "\n".join(f"- {b}" for b in bullets[:4])
        + f"\n\nCTA: Revisa la fuente completa y evalúa el impacto en tu operación.\n{cite}"
    )
    body_json = {"format": "video_script", "duration_hint_sec": 75, "bullets": bullets[:4]}
    new_title = f"Guion: {title[:80]}"
    return body, body_json, new_title


def _draft_carousel(summary: str, bullets: list[str], cite: str, title: str) -> tuple[str, dict, str]:
    fact1 = bullets[0] if bullets else summary
    fact2 = bullets[1] if len(bullets) > 1 else (title or summary)
    fact3 = bullets[2] if len(bullets) > 2 else summary
    slides = [
        {
            "slide": 1,
            "title": "El problema",
            "text": f"Lo que está pasando: {summary[:200]}",
            "content": f"Lo que está pasando: {summary[:200]}",
        },
        {
            "slide": 2,
            "title": "Hecho clave",
            "text": str(fact1)[:220],
            "content": str(fact1)[:220],
        },
        {
            "slide": 3,
            "title": "Riesgo / tensión",
            "text": f"Implicación para líderes: {str(fact2)[:180]}",
            "content": f"Implicación para líderes: {str(fact2)[:180]}",
        },
        {
            "slide": 4,
            "title": "Mi perspectiva",
            "text": (
                f"No basta con enterarse. Hay que traducir esto a control, "
                f"gobernanza y decisión: {str(fact3)[:140]}"
            ),
            "content": (
                f"No basta con enterarse. Hay que traducir esto a control, "
                f"gobernanza y decisión: {str(fact3)[:140]}"
            ),
        },
        {
            "slide": 5,
            "title": "Acción",
            "text": (
                "Pregunta para tu mesa: ¿quién valida el impacto en compliance "
                f"antes de escalar? {cite}"
            ),
            "content": (
                "Pregunta para tu mesa: ¿quién valida el impacto en compliance "
                f"antes de escalar? {cite}"
            ),
        },
    ]
    body = "\n\n".join(f"{s['title']}: {s['text']}" for s in slides)
    body_json = {"format": "carousel", "slides": slides}
    new_title = f"Carrusel: {title[:80]}"
    return body, body_json, new_title


def _draft_newsletter(summary: str, bullets: list[str], cite: str, title: str) -> tuple[str, dict, str]:
    takeaways = bullets[:4]
    body = (
        f"Asunto: {title[:90]}\n\n"
        f"{summary}\n\n"
        "Takeaways:\n"
        + "\n".join(f"- {t}" for t in takeaways)
        + f"\n\n{cite}"
    )
    body_json = {
        "format": "newsletter",
        "subject": title[:90],
        "takeaways": takeaways,
    }
    new_title = f"Newsletter: {title[:80]}"
    return body, body_json, new_title


def _deterministic_draft(
    article: NewsArticle,
    format_type: str,
    language: str,
) -> dict[str, Any]:
    """Fallback sin LLM: solo reformatea hechos ya guardados (cero invención)."""
    summary = article.summary or article.title
    facts = _key_facts(article)
    bullets = facts[:5] or [summary]
    cite = f"Fuente: {article.source_name} — {article.source_url}"
    title = article.title or ""

    if format_type == "linkedin":
        body, body_json, new_title = _draft_linkedin(summary, bullets, cite, title)
    elif format_type == "video_script":
        body, body_json, new_title = _draft_video_script(summary, bullets, cite, title)
    elif format_type == "carousel":
        body, body_json, new_title = _draft_carousel(summary, bullets, cite, title)
    else:  # newsletter
        body, body_json, new_title = _draft_newsletter(summary, bullets, cite, title)

    if language == "en":
        # Marcamos EN sin traducir con modelo: prefijo explícito (sin inventar)
        new_title = f"[EN draft from verified ES source] {new_title}"
        body = f"[Based strictly on verified source material]\n\n{body}"

    return {
        "article_id": article.id,
        "source_url": article.source_url,
        "format_type": format_type,
        "language": language,
        "title": new_title,
        "body_text": body,
        "body_json": body_json,
        "key_claims": bullets,
        "generation_mode": "deterministic",
    }


def _llm_draft(
    db: Session,
    article: NewsArticle,
    format_type: str,
    language: str,
    provider_mode: str = "auto",
) -> dict[str, Any]:
    import random
    from datetime import datetime

    from app.services.argumentative_critic import ArgumentativeCriticService

    facts = _key_facts(article)
    # Ángulo distinto en cada generación (evita el mismo LinkedIn una y otra vez)
    angle = random.choice(NARRATIVE_ANGLES)
    uniq = datetime.utcnow().strftime("%H%M%S")
    format_kwargs = {
        "client_name": settings.client_name,
        "article_id": article.id,
        "source_url": article.source_url,
        "format_type": format_type,
        "language": language,
        "language_instruction": language_instruction(language),
        "narrative_angle": (
            f"{angle} Variación #{uniq}. "
            f"OBLIGATORIO: el contenido debe tratar SOLO el tema de este artículo "
            f"(«{article.title[:120]}»). No menciones Global Business Navigator, "
            f"Incoterms ni Shipping Basics salvo que sean el tema literal del texto fuente. "
            f"IDIOMA: {language_instruction(language)}"
        ),
        "summary": article.summary or "",
        "key_facts": json.dumps(facts, ensure_ascii=False),
        # Menos contexto = menos prompt_eval en Ollama (ganancia grande en CPU local)
        "full_text": (article.full_text or "")[:3500],
        "persona_block": _persona_block_for_article(db, article),
    }
    from app.services.legal_seo_service import resolve_generation_prompt

    prompt, prompt_template_id = resolve_generation_prompt(
        db,
        organization_id=getattr(article, "organization_id", None),
        channel=format_type,
        format_kwargs=format_kwargs,
        fallback=GENERATION_PROMPT,
    )
    raw, model_used = _call_model(
        db, "generate_content", prompt, provider_mode=provider_mode
    )
    data = _extract_json(raw)

    # Gemma a menudo cambia article_id/source_url → no tumbar a plantilla por eso
    data["article_id"] = article.id
    data["source_url"] = article.source_url
    data["format_type"] = format_type
    data["language"] = language or data.get("language") or "es"
    if prompt_template_id:
        data["prompt_template_id"] = prompt_template_id

    if not data.get("body_text") or not data.get("title"):
        raise ValueError("Generation rejected: missing title/body_text")

    source_excerpt = (article.full_text or article.summary or "")[:5000]
    paraphrase_ratio = grounding_score(str(data.get("body_text") or ""), source_excerpt)
    has_perspective = "mi perspectiva" in str(data.get("body_text") or "").lower()

    # Crítico argumentativo (opcional, formatos largos)
    critique_result: dict[str, Any] = {
        "skip_rewrite": True,
        "provider_failed": False,
        "critique": "Crítica omitida.",
        "paraphrase_ratio": round(paraphrase_ratio, 3),
    }
    if settings.content_critic_enabled and format_type in {"carousel", "newsletter"}:
        try:
            critic = ArgumentativeCriticService(db)
            critique_result = critic.evaluate_argument(
                draft_text=data.get("body_text", ""),
                source_text=article.full_text or "",
            )
            critique_result["paraphrase_ratio"] = round(paraphrase_ratio, 3)
        except Exception as exc:  # noqa: BLE001
            critique_result = {
                "skip_rewrite": True,
                "provider_failed": True,
                "critique": f"Crítico omitido: {exc}",
                "paraphrase_ratio": round(paraphrase_ratio, 3),
            }

    needs_argument_rewrite = (
        not critique_result.get("skip_rewrite")
        and not critique_result.get("provider_failed")
        and critique_result.get("argumentative_score", 100) < 80
        and format_type != "linkedin"
    )
    # LinkedIn: una sola reescritura si es parafraseo o falta "Mi perspectiva"
    needs_linkedin_depth = format_type == "linkedin" and (
        paraphrase_ratio >= 0.62 or not has_perspective
    )

    if needs_argument_rewrite or needs_linkedin_depth:
        if needs_linkedin_depth:
            rewrite_prompt = LINKEDIN_REWRITE_PROMPT.format(
                persona_block=format_kwargs["persona_block"],
                article_id=article.id,
                source_url=article.source_url,
                language=language,
                language_instruction=language_instruction(language),
                angle=angle,
                title=article.title,
                raw_draft=str(data.get("body_text") or "")[:3500],
                key_facts=json.dumps(facts, ensure_ascii=False),
            )
        else:
            rewrite_prompt = get_rewrite_prompt(
                format_type=format_type,
                critique=critique_result.get("critique", ""),
                suggestions=critique_result.get("suggestions", []),
                angle=angle,
                title=article.title,
                article_id=article.id,
                source_url=article.source_url,
                raw_draft=raw,
            )
        raw_retry, retry_model = _call_model(
            db, "generate_content", rewrite_prompt, provider_mode=provider_mode
        )
        try:
            data_retry = _extract_json(raw_retry)
            if data_retry.get("body_text"):
                data_retry["article_id"] = article.id
                data_retry["source_url"] = article.source_url
                data_retry["format_type"] = format_type
                data_retry["language"] = language
                data = data_retry
                model_used = retry_model
                data["was_rewritten"] = True
                critique_result["note"] = (
                    "Reescrito: más análisis / menos paráfrasis."
                    if needs_linkedin_depth
                    else "Reescrito tras crítica."
                )
                critique_result["paraphrase_ratio_after"] = round(
                    grounding_score(str(data.get("body_text") or ""), source_excerpt),
                    3,
                )
        except Exception:
            pass

    data["argumentative_analysis"] = critique_result
    data["narrative_angle"] = angle
    data["generation_mode"] = "gateway"
    data["model_used"] = model_used
    data["provider_mode"] = provider_mode
    data["prompt_hash"] = _prompt_hash(prompt)

    body = str(data["body_text"])
    # Bloquear “pegamento” al post viejo de GBN si el artículo NO es ese
    title_l = (article.title or "").lower()
    body_l = body.lower()
    if (
        "global business navigator" in body_l
        and "global business navigator" not in title_l
        and "navigator" not in (article.full_text or "")[:2000].lower()
    ):
        raise ValueError("Generation rejected: off-topic Global Business Navigator paste")

    if article.source_url not in body and "fuente" not in body.lower():
        data["body_text"] = body.rstrip() + f"\n\nFuente: {article.source_url}"

    if format_type == "carousel":
        data["body_json"] = _normalize_carousel_body_json(data.get("body_json"), data.get("body_text"))

    return data


def _normalize_carousel_body_json(body_json: Any, body_text: Any) -> dict[str, Any]:
    """Unifica slides a [{slide, title, text, content}] para la UI."""
    raw = body_json
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = None
    slides = None
    if isinstance(raw, list):
        slides = raw
    elif isinstance(raw, dict):
        slides = raw.get("slides")
    if not isinstance(slides, list) or not slides:
        text = str(body_text or "").strip()
        slides = [{"title": "Carrusel", "text": text[:500]}] if text else []
    normalized = []
    for i, s in enumerate(slides, start=1):
        if isinstance(s, str):
            normalized.append(
                {"slide": i, "title": f"Diapositiva {i}", "text": s, "content": s}
            )
            continue
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or s.get("headline") or f"Diapositiva {i}")
        content = str(s.get("content") or s.get("text") or s.get("body") or "")
        normalized.append(
            {
                "slide": int(s.get("slide") or i),
                "title": title,
                "text": content,
                "content": content,
            }
        )
    return {"format": "carousel", "slides": normalized}


def _llm_package_drafts(
    db: Session,
    article: NewsArticle,
    language: str,
    provider_mode: str = "auto",
) -> dict[str, dict[str, Any]]:
    """Genera los cuatro formatos en una sola inferencia; faltantes usan fallback."""
    facts = _key_facts(article)
    prompt = f"""
Eres el editor senior de {settings.client_name}. Crea un paquete editorial
basado EXCLUSIVAMENTE en la fuente verificada.

IDIOMA OBLIGATORIO DE SALIDA: {language_instruction(language)}
Código de idioma a guardar en cada pieza: {language}

Devuelve SOLO JSON estricto con esta forma:
{{
  "pieces": [
    {{
      "format_type": "linkedin|video_script|carousel|newsletter",
      "title": "...",
      "body_text": "...",
      "body_json": {{}},
      "key_claims": ["..."]
    }}
  ]
}}

Incluye exactamente una pieza por formato: linkedin, video_script, carousel y
newsletter. LinkedIn debe tener gancho, análisis y CTA; video_script debe incluir
hook, desarrollo y cierre; carousel debe incluir body_json.slides; newsletter
debe incluir asunto, análisis y takeaways. Cita la URL fuente y no inventes datos.
Todo el texto generado (títulos y cuerpos) debe cumplir el idioma obligatorio.

ARTÍCULO: {article.title}
RESUMEN: {article.summary or ""}
HECHOS VERIFICADOS: {json.dumps(facts, ensure_ascii=False)}
FUENTE: {article.source_url}
TEXTO: {(article.full_text or "")[:3500]}
"""
    raw, model_used = _call_model(
        db, "generate_content_batch", prompt, provider_mode=provider_mode
    )
    data = _extract_json(raw)
    pieces = data.get("pieces")
    if not isinstance(pieces, list):
        raise ValueError("Batch generation rejected: missing pieces")

    drafts: dict[str, dict[str, Any]] = {}
    for item in pieces:
        if not isinstance(item, dict):
            continue
        format_type = str(item.get("format_type") or "").strip()
        if format_type not in FORMATS or format_type in drafts:
            continue
        if not item.get("title") or not item.get("body_text"):
            continue
        body = str(item["body_text"])
        if article.source_url not in body and "fuente" not in body.lower():
            body = body.rstrip() + f"\n\nFuente: {article.source_url}"
        item.update(
            {
                "article_id": article.id,
                "source_url": article.source_url,
                "format_type": format_type,
                "language": language,
                "body_text": body,
                "generation_mode": "gateway_batch",
                "model_used": model_used,
                "prompt_hash": _prompt_hash(prompt),
                "argumentative_analysis": {
                    "skip_rewrite": True,
                    "provider_failed": False,
                    "critique": "Crítica separada desactivada en modo de generación agrupada.",
                },
            }
        )
        if format_type == "carousel":
            item["body_json"] = _normalize_carousel_body_json(
                item.get("body_json"),
                item.get("body_text"),
            )
        drafts[format_type] = item
    if not drafts:
        raise ValueError("Batch generation rejected: no valid pieces")
    return drafts


def generate_piece_payload(
    article: NewsArticle,
    format_type: str,
    language: str = "es",
    prefer_llm: bool = True,
    db: Session | None = None,
    provider_mode: str = "auto",
) -> dict[str, Any]:
    if prefer_llm and db is not None:
        try:
            return _llm_draft(
                db, article, format_type, language, provider_mode=provider_mode
            )
        except Exception as exc:
            draft = _deterministic_draft(article, format_type, language)
            draft["llm_error"] = str(exc)
            return draft
    if prefer_llm and db is None:
        # sin sesión no hay gateway; draft determinístico
        draft = _deterministic_draft(article, format_type, language)
        draft["llm_error"] = "no_db_session_for_gateway"
        return draft
    return _deterministic_draft(article, format_type, language)


def _save_piece(
    db: Session,
    *,
    package: ContentPackage,
    article: NewsArticle,
    payload: dict[str, Any],
    parent_piece_id: int | None = None,
) -> ContentPiece:
    piece = ContentPiece(
        organization_id=package.organization_id or getattr(article, "organization_id", None),
        package_id=package.id,
        article_id=article.id,
        parent_piece_id=parent_piece_id,
        format_type=payload["format_type"],
        language=payload.get("language") or "es",
        title=str(payload["title"])[:512],
        body_text=str(payload["body_text"]),
        body_json=payload.get("body_json"),
        source_url=article.source_url,
        status="draft",
        version=1,
        generation_json=payload,
    )
    db.add(piece)
    db.flush()
    run_reviews(db, piece, article)

    log_audit(
        db,
        entity_type="content_piece",
        entity_id=piece.id,
        action="generated",
        model_used=(
            (payload.get("model_used") or settings.ollama_model)
            if payload.get("generation_mode") == "gateway"
            else "deterministic"
        ),
        source_url=article.source_url,
        output_summary=piece.title[:300],
        metadata_json={
            "format_type": piece.format_type,
            "status": piece.status,
            "generation_mode": payload.get("generation_mode"),
        },
    )
    return piece


def create_content_package(
    db: Session,
    article: NewsArticle,
    *,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
    profile: ProfessionalProfile | None = None,
    organization_id: int | None = None,
    formats: list[str] | None = None,
    package_id: int | None = None,
    regenerate: bool = False,
    provider_mode: str = "auto",
) -> ContentPackage:
    started = time.perf_counter()
    if article.status not in ("verified", "approved", "published", "collected", "classified"):
        raise ValueError(
            f"Article must be collected/verified before content generation (status={article.status})"
        )

    profile = profile or get_active_profile(db)
    languages = languages or ["es"]
    wanted = [f for f in (formats or list(FORMATS)) if f in FORMATS]
    if not wanted:
        wanted = list(FORMATS)

    package: ContentPackage | None = None
    if package_id is not None:
        package = (
            db.query(ContentPackage)
            .filter(
                ContentPackage.id == package_id,
                ContentPackage.article_id == article.id,
            )
            .first()
        )
        if not package:
            raise ValueError("Package not found for article")
    else:
        # Reutilizar el paquete más reciente del artículo (generación por etapas)
        q = db.query(ContentPackage).filter(ContentPackage.article_id == article.id)
        if organization_id is not None:
            q = q.filter(ContentPackage.organization_id == organization_id)
        package = q.order_by(ContentPackage.id.desc()).first()

    if package is None:
        package = ContentPackage(
            organization_id=organization_id or getattr(article, "organization_id", None),
            article_id=article.id,
            profile_id=profile.id if profile else None,
            status="reviewing",
        )
        db.add(package)
        db.flush()
    else:
        package.status = "reviewing"
        db.flush()

    for lang in languages:
        batch_drafts: dict[str, dict[str, Any]] = {}
        batch_duration_ms = 0
        # Batch LLM solo tiene sentido si pedimos los 4 formatos de una vez
        use_batch = (
            prefer_llm
            and settings.content_batch_generation_enabled
            and set(wanted) == set(FORMATS)
        )
        if use_batch:
            batch_started = time.perf_counter()
            try:
                batch_drafts = _llm_package_drafts(
                    db, article, lang, provider_mode=provider_mode
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "content_batch_fallback article_id=%s language=%s error=%s",
                    article.id,
                    lang,
                    str(exc)[:300],
                )
            batch_duration_ms = round(
                (time.perf_counter() - batch_started) * 1000
            )
        for fmt in wanted:
            existing = (
                db.query(ContentPiece)
                .filter(
                    ContentPiece.package_id == package.id,
                    ContentPiece.format_type == fmt,
                    ContentPiece.language == lang,
                )
                .order_by(ContentPiece.id.desc())
                .first()
            )
            if existing and not regenerate:
                continue
            piece_started = time.perf_counter()
            payload = batch_drafts.get(fmt)
            if payload is None:
                payload = generate_piece_payload(
                    article,
                    fmt,
                    language=lang,
                    prefer_llm=prefer_llm,
                    db=db,
                    provider_mode=provider_mode,
                )
            elif batch_duration_ms:
                payload["batch_duration_ms"] = batch_duration_ms
            payload["duration_ms"] = round((time.perf_counter() - piece_started) * 1000)
            _save_piece(db, package=package, article=article, payload=payload)

    _refresh_package_status(package, db)
    db.commit()
    db.refresh(package)
    logger.info(
        "content_package_complete package_id=%s article_id=%s formats=%s languages=%s duration_ms=%s",
        package.id,
        article.id,
        wanted,
        languages,
        round((time.perf_counter() - started) * 1000),
    )
    return package


def reuse_approved_piece(
    db: Session,
    piece: ContentPiece,
    *,
    target_formats: list[str] | None = None,
    prefer_llm: bool = True,
) -> list[ContentPiece]:
    """Agente reutilizador: de una pieza aprobada genera 3–5 derivados."""
    if piece.status != "approved":
        raise ValueError("Only approved pieces can be reused")

    article = db.query(NewsArticle).filter(NewsArticle.id == piece.article_id).first()
    if not article:
        raise ValueError("Source article missing")

    package = db.query(ContentPackage).filter(ContentPackage.id == piece.package_id).first()
    if not package:
        raise ValueError("Package missing")

    targets = target_formats or [f for f in FORMATS if f != piece.format_type]
    # Añadir short_post / thread como derivados extras
    extras = ["short_post", "thread"]
    for e in extras:
        if e not in targets and len(targets) < 5:
            targets.append(e)

    created: list[ContentPiece] = []
    for fmt in targets[:5]:
        if fmt in ("short_post", "thread"):
            payload = _deterministic_derivative(article, piece, fmt)
        else:
            payload = generate_piece_payload(
                article, fmt, language=piece.language, prefer_llm=prefer_llm, db=db
            )
        created.append(
            _save_piece(
                db,
                package=package,
                article=article,
                payload=payload,
                parent_piece_id=piece.id,
            )
        )

    _refresh_package_status(package, db)
    db.commit()
    return created


def _deterministic_derivative(
    article: NewsArticle, parent: ContentPiece, format_type: str
) -> dict[str, Any]:
    cite = f"Fuente: {article.source_url}"
    base = parent.body_text[:500]
    if format_type == "short_post":
        body = f"{article.title}\n\n{article.summary or base[:280]}\n\n{cite}"
        title = f"Short: {article.title[:70]}"
    else:
        lines = [article.title, ""]
        for i, claim in enumerate((article.classification_json or {}).get("key_facts") or [], 1):
            lines.append(f"{i}/ {claim}")
            if i >= 5:
                break
        lines.extend(["", cite])
        body = "\n".join(lines)
        title = f"Thread: {article.title[:70]}"
    return {
        "article_id": article.id,
        "source_url": article.source_url,
        "format_type": format_type,
        "language": parent.language,
        "title": title,
        "body_text": body,
        "body_json": {"derived_from": parent.id, "format": format_type},
        "key_claims": (article.classification_json or {}).get("key_facts") or [],
        "generation_mode": "deterministic_reuse",
    }


def translate_piece(
    db: Session,
    piece: ContentPiece,
    target_lang: str = "en",
    prefer_llm: bool = True,
) -> ContentPiece:
    article = db.query(NewsArticle).filter(NewsArticle.id == piece.article_id).first()
    if not article:
        raise ValueError("Article not found")
    package = db.query(ContentPackage).filter(ContentPackage.id == piece.package_id).first()
    if not package:
        raise ValueError("Package not found")

    payload = generate_piece_payload(
        article, piece.format_type, language=target_lang, prefer_llm=prefer_llm, db=db
    )
    # Post-traducción: misma verificación factual
    new_piece = _save_piece(
        db,
        package=package,
        article=article,
        payload=payload,
        parent_piece_id=piece.id,
    )
    _refresh_package_status(package, db)
    db.commit()
    return new_piece


def _refresh_package_status(package: ContentPackage, db: Session | None = None) -> None:
    if db is not None:
        pieces = (
            db.query(ContentPiece)
            .filter(ContentPiece.package_id == package.id)
            .all()
        )
    else:
        pieces = list(package.pieces or [])
    if not pieces:
        package.status = "draft"
        return
    statuses = {p.status for p in pieces}
    if statuses and statuses <= {"approved"}:
        package.status = "approved"
    elif "pending_approval" in statuses and not (
        statuses & {"factual_failed", "brand_failed", "draft"}
    ):
        package.status = "pending_approval"
    elif statuses & {"factual_failed", "brand_failed"}:
        package.status = "partial"
    elif "approved" in statuses:
        package.status = "partial"
    else:
        package.status = "reviewing"
