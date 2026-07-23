import hashlib
import json
import re

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NewsArticle
from app.services.audit import log_audit

_STOPWORDS = {
    "para", "como", "esta", "este", "entre", "sobre", "tras", "desde", "hasta",
    "hacia", "segun", "tienen", "tiene", "donde", "quien", "pero", "por", "con",
    "sin", "las", "los", "una", "uno", "unos", "unas", "del", "que", "the", "and",
    "for", "with", "from", "that", "this", "are", "was", "were", "have", "has",
}


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError("Model did not return valid JSON")


def _call_ollama(prompt: str) -> str:
    """Compat: llamada directa a Ollama (sin DB / sin gateway)."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    with httpx.Client(timeout=settings.llm_request_timeout_seconds) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["message"]["content"]


def _call_model(db: Session, task_type: str, prompt: str) -> tuple[str, str]:
    """Gateway Fase 5. Retorna (texto, model_used)."""
    from app.services.fase5_ai import complete

    text, meta = complete(db, task_type=task_type, prompt=prompt)
    return text, str(meta.get("model_used") or settings.ollama_model)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-záéíóúñü0-9]{3,}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def grounding_score(claim: str, source_text: str) -> float:
    """Overlap determinístico claim ↔ fuente. No usa el modelo."""
    claim_tokens = _tokens(claim)
    if not claim_tokens:
        return 1.0
    source_tokens = _tokens(source_text)
    hits = sum(1 for t in claim_tokens if t in source_tokens)
    return hits / len(claim_tokens)


def apply_deterministic_grounding(data: dict, source_text: str) -> dict:
    """
    Segunda puerta anti-alucinación: el backend puede forzar publishable=false
    aunque el modelo diga lo contrario, si el overlap lexical falla.

    Bilingüe MX-US: si el claim está en español y la fuente en inglés, se acepta
    anclaje vía el campo evidence (cita en idioma de la fuente).
    """
    unsupported: list[str] = []
    facts = data.get("facts") or []
    revised_facts = []
    supported_count = 0

    for fact in facts:
        if isinstance(fact, dict):
            claim = str(fact.get("claim", ""))
            evidence = str(fact.get("evidence") or "")
            claim_score = grounding_score(claim, source_text)
            evidence_score = grounding_score(evidence, source_text) if evidence.strip() else 0.0
            score = max(claim_score, evidence_score)
            model_ok = bool(fact.get("supported", True))
            supported = score >= 0.35 and (model_ok or evidence_score >= 0.35)
            revised = {
                **fact,
                "supported": supported,
                "grounding_score": round(score, 3),
                "claim_grounding_score": round(claim_score, 3),
                "evidence_grounding_score": round(evidence_score, 3),
            }
            revised_facts.append(revised)
            if supported:
                supported_count += 1
            elif claim:
                unsupported.append(claim)
        else:
            claim = str(fact)
            score = grounding_score(claim, source_text)
            ok = score >= 0.35
            revised_facts.append(
                {"claim": claim, "supported": ok, "grounding_score": round(score, 3)}
            )
            if ok:
                supported_count += 1
            else:
                unsupported.append(claim)

    summary = str(data.get("summary") or "")
    summary_score = grounding_score(summary, source_text) if summary else 1.0
    fact_ratio = (supported_count / len(revised_facts)) if revised_facts else 0.0
    # Resumen traducido: permitir si la mayoría de hechos anclan a la fuente
    summary_verified = bool(data.get("summary_verified", True)) and (
        summary_score >= 0.30 or (fact_ratio >= 0.7 and summary_score >= 0.05)
    )

    if not summary_verified and summary:
        unsupported.append("summary_not_grounded")

    # dedupe / limpia basura del modelo
    seen: set[str] = set()
    unique_unsupported: list[str] = []
    for item in unsupported:
        key = str(item).strip().lower()
        if not key or key in {"[]", "null", "none"}:
            continue
        if key not in seen:
            seen.add(key)
            unique_unsupported.append(item)

    data["facts"] = revised_facts
    data["unsupported_claims"] = unique_unsupported
    data["summary_verified"] = summary_verified
    data["summary_grounding_score"] = round(summary_score, 3)
    data["fact_support_ratio"] = round(fact_ratio, 3)
    data["publishable"] = bool(summary_verified and len(unique_unsupported) == 0)
    return data


CLASSIFICATION_PROMPT = """Eres un analista editorial para {client_name}.
Trabajas SOLO con el texto proporcionado. NO uses conocimiento externo.

Enfoque: IA, gobernanza, empresas, PI y eje México–EE.UU.
Tipologías editoriales válidas (elige la mejor o null):
1 politica-regulacion-ia | 2 ia-mal-implementada | 3 casos-legales-ia |
4 ia-exito-empresarial | 5 empresas-rezagadas-ia | 6 patentes-pi-ia |
7 inversiones-ia | 8 privacidad-ciberseguridad-ia | 9 empleo-transformacion-ia |
10 ia-abogados-legal | 11 mexico-estados-unidos-ia

Devuelve JSON estricto con estas claves:
- article_id (número entero, debe ser exactamente {article_id})
- source_url (string, debe ser exactamente "{source_url}")
- summary (string, máximo 120 palabras, solo hechos del texto)
- news_type_id (entero 1-11 o null si no encaja)
- news_type_slug (string o null)
- scores (objeto con valores 0-100):
  - relevance
  - impact
  - reliability
  - freshness
  - content_potential
  - mx_us_relevance
  - conversion
- pillars (array de strings, máximo 3 pilares editoriales detectados)
- key_facts (array de strings, cada hecho debe ser verificable en el texto)
- editorial_angle (string: qué debería revisar una empresa a partir de esta noticia)

TEXTO:
\"\"\"
{full_text}
\"\"\"
"""


VERIFICATION_PROMPT = """Eres un verificador factual anti-alucinación.

Compara el RESUMEN y los KEY_FACTS contra el TEXTO ORIGINAL.
Marca cada afirmación como supported=true solo si aparece explícita o implícitamente en el texto.

Devuelve JSON estricto:
- article_id (entero, debe ser {article_id})
- source_url (string, debe ser "{source_url}")
- summary_verified (boolean)
- facts (array de objetos: claim, supported, evidence)
- unsupported_claims (array de strings)
- publishable (boolean, true solo si summary_verified=true y unsupported_claims está vacío)

RESUMEN:
{summary}

KEY_FACTS:
{key_facts}

TEXTO ORIGINAL:
\"\"\"
{full_text}
\"\"\"
"""


def classify_article(db: Session, article: NewsArticle) -> dict:
    prompt = CLASSIFICATION_PROMPT.format(
        client_name=settings.client_name,
        article_id=article.id,
        source_url=article.source_url,
        full_text=article.full_text[:12000],
    )
    raw, model_used = _call_model(db, "classify", prompt)
    data = _extract_json(raw)

    if data.get("article_id") != article.id:
        raise ValueError("Classification rejected: article_id mismatch")
    if data.get("source_url") != article.source_url:
        raise ValueError("Classification rejected: source_url mismatch")
    if "scores" not in data or "summary" not in data:
        raise ValueError("Classification rejected: missing required fields")

    scores = data["scores"]
    # Preservar metadata del Scout si ya existía
    prev = article.classification_json or {}
    if isinstance(prev, dict) and prev.get("scout") and not data.get("scout"):
        data["scout"] = prev["scout"]
        if not data.get("news_type_id") and prev["scout"].get("news_type_id"):
            data["news_type_id"] = prev["scout"]["news_type_id"]
            data["news_type_slug"] = prev["scout"].get("news_type_slug")
    article.classification_json = data
    article.summary = data["summary"]
    article.score_relevance = float(scores.get("relevance", 0))
    article.score_impact = float(scores.get("impact", 0))
    article.score_reliability = float(scores.get("reliability", 0))
    article.score_freshness = float(scores.get("freshness", 0))
    article.score_content_potential = float(scores.get("content_potential", 0))
    article.score_mx_us_relevance = float(scores.get("mx_us_relevance", 0))
    article.score_conversion = float(scores.get("conversion", 0))
    article.status = "classified"

    log_audit(
        db,
        entity_type="news_article",
        entity_id=article.id,
        action="classified",
        model_used=model_used,
        source_url=article.source_url,
        prompt_hash=_prompt_hash(prompt),
        output_summary=data["summary"][:300],
        metadata_json={"scores": scores},
    )
    db.commit()
    return data


def verify_article(db: Session, article: NewsArticle) -> dict:
    if not article.classification_json:
        raise ValueError("Article must be classified before verification")

    key_facts = article.classification_json.get("key_facts", [])
    prompt = VERIFICATION_PROMPT.format(
        article_id=article.id,
        source_url=article.source_url,
        summary=article.summary or "",
        key_facts=json.dumps(key_facts, ensure_ascii=False),
        full_text=article.full_text[:12000],
    )
    raw, model_used = _call_model(db, "verify", prompt)
    data = _extract_json(raw)

    if data.get("article_id") != article.id:
        raise ValueError("Verification rejected: article_id mismatch")
    if data.get("source_url") != article.source_url:
        raise ValueError("Verification rejected: source_url mismatch")

    # Gate determinístico: el código manda sobre el modelo
    data = apply_deterministic_grounding(data, article.full_text or "")

    article.verification_json = data
    article.status = "verified" if data.get("publishable") else "rejected"

    log_audit(
        db,
        entity_type="news_article",
        entity_id=article.id,
        action="verified" if data.get("publishable") else "rejected",
        model_used=model_used,
        source_url=article.source_url,
        prompt_hash=_prompt_hash(prompt),
        metadata_json=data,
    )
    db.commit()
    return data


def process_unclassified(
    db: Session,
    limit: int = 20,
    organization_id: int | None = None,
) -> dict:
    query = db.query(NewsArticle).filter(NewsArticle.status == "collected")
    if organization_id is not None:
        query = query.filter(NewsArticle.organization_id == organization_id)
    articles = query.order_by(NewsArticle.created_at.desc()).limit(limit).all()
    classified = 0
    verified = 0
    rejected = 0
    errors = []

    for article in articles:
        try:
            classify_article(db, article)
            classified += 1
            result = verify_article(db, article)
            if result.get("publishable"):
                verified += 1
            else:
                rejected += 1
        except Exception as exc:
            errors.append({"article_id": article.id, "error": str(exc)})

    return {
        "processed": len(articles),
        "classified": classified,
        "verified": verified,
        "rejected": rejected,
        "errors": errors,
    }
