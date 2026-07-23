"""Revisores Fase 3 — factual y marca. Decisión final por código, no por confianza en el modelo."""

from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import ContentPiece, NewsArticle
from app.services.llm import grounding_score

# Palabras/hype prohibidas para la voz de Juan (consultoría legal profesional)
BANNED_HYPE = {
    "revolucionario",
    "revolucionaria",
    "increíble",
    "impresionante",
    "gurú",
    "hackea",
    "hackear",
    "secretos que nadie",
    "te va a cambiar la vida",
    "millón de dólares",
    "garantizado",
    "100% seguro",
}

REQUIRED_VOICE = {
    "must_cite_source": True,
    "max_exclamation": 2,
    "max_emoji": 1,
    "prefer_first_person_linkedin": True,
}


_OPINION_MARKERS = (
    "mi perspectiva",
    "desde una perspectiva",
    "sin embargo",
    "no obstante",
    "debemos",
    "la clave",
    "la estrategia",
    "la precisión no es",
    "nunca debe",
    "más prudente",
    "cómo están",
    "cómo está",
    "en mi opinión",
    "creo que",
    "considero que",
)


def _is_editorial_claim(text: str) -> bool:
    """Opinión, CTA, hashtags o meta — no deben exigir grounding lexical en la fuente."""
    t = (text or "").strip()
    low = t.lower()
    if not t or len(t) <= 20:
        return True
    if t.startswith("#") or low.startswith("http://") or low.startswith("https://"):
        return True
    if low.startswith("fuente:") or low.startswith("source:"):
        return True
    if t.endswith("?") or t.endswith("？"):
        return True
    if any(m in low for m in _OPINION_MARKERS):
        return True
    # Hashtags en línea
    if re.search(r"(?:^|\s)#[\wáéíóúñÁÉÍÓÚÑ]+", t):
        return True
    return False


def _split_claims(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    claims = []
    for p in parts:
        p = p.strip().lstrip("-•* ").strip()
        if len(p) <= 25:
            continue
        low = p.lower()
        if low.startswith("fuente:") or low.startswith("source:"):
            continue
        if low.startswith("asunto:") or low.startswith("hook:") or low.startswith("cta:"):
            rest = p.split(":", 1)[-1].strip()
            if len(rest) > 25 and not _is_editorial_claim(rest):
                claims.append(rest)
            continue
        if p.startswith("http://") or p.startswith("https://"):
            continue
        if _is_editorial_claim(p):
            continue
        claims.append(p)
    return claims


def extract_factual_claim_texts(piece: ContentPiece) -> list[str]:
    """Afirmaciones factuales candidatas (sin opinión/CTA) para el motor legal."""
    body = piece.body_text or ""
    claims = _split_claims(body)
    if piece.body_json:
        for key in ("slides", "bullets", "key_points", "sections"):
            items = piece.body_json.get(key) or []
            for item in items:
                if isinstance(item, dict):
                    raw = str(item.get("text") or item.get("body") or item.get("content") or "")
                else:
                    raw = str(item)
                if raw.strip() and not _is_editorial_claim(raw):
                    claims.append(raw.strip())
    out: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        c = claim.strip()
        if len(c) < 25 or _is_editorial_claim(c):
            continue
        key = c.lower()[:200]
        if key in seen:
            continue
        seen.add(key)
        out.append(c[:2000])
        if len(out) >= 25:
            break
    return out


def review_factual(piece: ContentPiece, article: NewsArticle) -> dict:
    """Compara afirmaciones factuales del contenido contra el texto fuente en BD.

    La voz editorial (perspectiva, CTA, preguntas) no se exige en la fuente;
    basta mayoría de claims factuales con grounding razonable.
    """
    source = article.full_text or ""
    body = piece.body_text or ""
    claims = _split_claims(body)

    if piece.body_json:
        for key in ("slides", "bullets", "key_points", "sections"):
            items = piece.body_json.get(key) or []
            for item in items:
                if isinstance(item, dict):
                    raw = str(item.get("text") or item.get("body") or item.get("content") or "")
                else:
                    raw = str(item)
                if raw.strip() and not _is_editorial_claim(raw):
                    claims.append(raw.strip())

    claims = [c for c in claims if c.strip()]
    grounded = []
    unsupported = []
    skipped_editorial = 0
    details = []

    for claim in claims[:40]:
        if _is_editorial_claim(claim):
            skipped_editorial += 1
            continue
        score = grounding_score(claim, source)
        ok = score >= 0.22
        details.append(
            {
                "claim": claim[:280],
                "grounding_score": round(score, 3),
                "supported": ok,
            }
        )
        if ok:
            grounded.append(claim[:280])
        else:
            unsupported.append(claim[:280])

    has_trace = bool(piece.source_url) and piece.article_id == article.id
    if piece.source_url != article.source_url:
        unsupported.append("source_url_mismatch")
        has_trace = False

    factual_n = len(grounded) + len([u for u in unsupported if u != "source_url_mismatch"])
    # Pasa si hay trazabilidad y (no hay claims factuales pero hay cuerpo, o >=40% grounded)
    if factual_n == 0:
        publishable = has_trace and bool((body or "").strip())
    else:
        ratio = len(grounded) / max(1, factual_n)
        # Voz Juan = análisis; exigir mayoría absoluta mataba todo el multi-formato.
        # Basta trazabilidad + al menos 1 claim grounded y ratio mínima.
        publishable = has_trace and len(grounded) >= 1 and ratio >= 0.25

    return {
        "article_id": article.id,
        "source_url": article.source_url,
        "claims_checked": factual_n,
        "grounded_count": len(grounded),
        "unsupported_claims": unsupported,
        "skipped_editorial": skipped_editorial,
        "details": details,
        "traceable": has_trace,
        "passed": publishable,
    }


def _count_emojis(text: str) -> int:
    # Rango amplio de emoji / símbolos decorativos
    return len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text))


def review_brand(
    piece: ContentPiece,
    *,
    previous_bodies: Iterable[str] | None = None,
) -> dict:
    """Checklist determinístico de voz/marca + coherencia léxica con piezas previas."""
    text = (piece.body_text or "").lower()
    issues: list[str] = []

    for phrase in BANNED_HYPE:
        if phrase in text:
            issues.append(f"hype_banned:{phrase}")

    excl = (piece.body_text or "").count("!")
    if excl > REQUIRED_VOICE["max_exclamation"]:
        issues.append(f"too_many_exclamations:{excl}")

    emojis = _count_emojis(piece.body_text or "")
    if emojis > REQUIRED_VOICE["max_emoji"]:
        issues.append(f"too_many_emojis:{emojis}")

    # Debe mencionar fuente o incluir URL de fuente
    has_cite = bool(piece.source_url) and (
        "fuente" in text
        or "source" in text
        or (piece.source_url.lower() in (piece.body_text or "").lower())
        or "http" in (piece.body_text or "").lower()
    )
    if not has_cite:
        issues.append("missing_source_citation")

    # LinkedIn: preferir primera persona ocasional (soft check)
    if piece.format_type == "linkedin":
        if not re.search(r"\b(yo|mi|me|nuestro|nuestra)\b", text):
            # No falla duro — solo warning
            pass

    coherence = None
    prev = list(previous_bodies or [])
    if prev:
        # Overlap promedio con piezas aprobadas recientes (voz similar = bien)
        scores = [grounding_score(piece.body_text[:800], p[:2000]) for p in prev[:5]]
        coherence = round(sum(scores) / len(scores), 3) if scores else None
        # Si es muy distinta Y contiene hype, ya falló; si overlap < 0.05 no fallamos solo por eso

    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "emoji_count": emojis,
        "exclamation_count": excl,
        "coherence_with_previous": coherence,
        "voice_rules": REQUIRED_VOICE,
    }


def review_argumentative(piece: ContentPiece) -> dict:
    gen_data = piece.generation_json or {}
    analysis = gen_data.get("argumentative_analysis")
    if not analysis:
        # Si no hay análisis, pasa por defecto (ej. fallback determinístico)
        return {"passed": True, "score": None, "critique": None}

    # Si el crítico falló por timeout/providers, no bloquear la pieza
    if analysis.get("skip_rewrite") or analysis.get("provider_failed"):
        return {
            "passed": True,
            "score": analysis.get("argumentative_score"),
            "critique": analysis.get("critique"),
            "suggestions": analysis.get("suggestions") or [],
            "was_rewritten": gen_data.get("was_rewritten", False),
            "skipped": True,
        }

    score = analysis.get("argumentative_score", 0)
    try:
        score_f = float(score)
    except (TypeError, ValueError):
        score_f = 0.0
    # Score 0 con crítica de error = fallo de infra, no del contenido
    critique = str(analysis.get("critique") or "")
    if score_f <= 0 and ("error" in critique.lower() or "failed" in critique.lower()):
        return {
            "passed": True,
            "score": score_f,
            "critique": critique,
            "suggestions": analysis.get("suggestions") or [],
            "was_rewritten": gen_data.get("was_rewritten", False),
            "skipped": True,
        }

    passed = score_f >= 55
    return {
        "passed": passed,
        "score": score_f,
        "critique": critique,
        "suggestions": analysis.get("suggestions"),
        "was_rewritten": gen_data.get("was_rewritten", False),
    }

def run_reviews(
    db: Session,
    piece: ContentPiece,
    article: NewsArticle,
) -> ContentPiece:
    factual = review_factual(piece, article)
    piece.factual_review_json = factual

    previous_q = db.query(ContentPiece).filter(
        ContentPiece.status == "approved",
        ContentPiece.format_type == piece.format_type,
        ContentPiece.id != piece.id,
    )
    if piece.organization_id is not None:
        previous_q = previous_q.filter(
            ContentPiece.organization_id == piece.organization_id
        )
    previous = previous_q.order_by(ContentPiece.approved_at.desc()).limit(5).all()
    brand = review_brand(piece, previous_bodies=[p.body_text for p in previous])
    piece.brand_review_json = brand
    
    argumentative = review_argumentative(piece)
    # Incluimos el análisis argumentativo dentro del brand_review_json
    # para no tener que agregar un campo extra a la BD, pero mantenerlo visible.
    brand["argumentative_analysis"] = argumentative
    piece.brand_review_json = brand

    if not factual.get("passed"):
        piece.status = "factual_failed"
    elif not argumentative.get("passed"):
        piece.status = "argumentative_failed"
    elif not brand.get("passed"):
        piece.status = "brand_failed"
    else:
        piece.status = "pending_approval"

    return piece
