"""Tests Fase 3 — revisores factual/marca y draft determinístico."""

from types import SimpleNamespace

from app.services.content_generation import _deterministic_draft
from app.services.content_review import review_brand, review_factual


def _article(**kwargs):
    base = {
        "id": 7,
        "title": "SEC anuncia reglas de disclosure para IA",
        "summary": "La SEC anunció nuevas reglas de disclosure para empresas de inteligencia artificial.",
        "full_text": (
            "La SEC anunció nuevas reglas de disclosure para empresas de inteligencia artificial "
            "en 2026. Las empresas deberán reportar riesgos materiales relacionados con modelos."
        ),
        "source_url": "https://example.com/sec-ia",
        "source_name": "SEC",
        "classification_json": {
            "key_facts": [
                "La SEC anunció nuevas reglas de disclosure",
                "Aplican a empresas de inteligencia artificial",
            ]
        },
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_deterministic_draft_keeps_source_trace():
    article = _article()
    draft = _deterministic_draft(article, "linkedin", "es")
    assert draft["article_id"] == 7
    assert draft["source_url"] == article.source_url
    assert article.source_url in draft["body_text"]
    assert "Fuente" in draft["body_text"]


def test_factual_review_passes_grounded_content():
    article = _article()
    draft = _deterministic_draft(article, "newsletter", "es")
    piece = SimpleNamespace(
        body_text=draft["body_text"],
        body_json=draft["body_json"],
        source_url=article.source_url,
        article_id=article.id,
    )
    result = review_factual(piece, article)
    assert result["traceable"] is True
    assert result["passed"] is True


def test_factual_review_rejects_hallucination():
    article = _article()
    piece = SimpleNamespace(
        body_text=(
            "El Congreso de México aprobó una reforma fiscal total y eliminó el IVA. "
            "Fuente: https://example.com/sec-ia"
        ),
        body_json=None,
        source_url=article.source_url,
        article_id=article.id,
    )
    result = review_factual(piece, article)
    assert result["passed"] is False
    assert len(result["unsupported_claims"]) > 0


def test_brand_review_rejects_hype():
    piece = SimpleNamespace(
        body_text="Este tip revolucionario te va a cambiar la vida!!! 🚀🚀🚀 Fuente: https://x.com",
        format_type="linkedin",
        source_url="https://x.com",
    )
    result = review_brand(piece)
    assert result["passed"] is False
    assert any("hype_banned" in i or "emoji" in i or "exclamation" in i for i in result["issues"])


def test_brand_review_accepts_professional_tone():
    piece = SimpleNamespace(
        body_text=(
            "La SEC anunció nuevas reglas de disclosure para IA. "
            "Conviene revisar el impacto en reportes corporativos. "
            "Fuente: https://example.com/sec-ia"
        ),
        format_type="linkedin",
        source_url="https://example.com/sec-ia",
    )
    result = review_brand(piece)
    assert result["passed"] is True
