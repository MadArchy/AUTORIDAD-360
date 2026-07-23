import json
from types import SimpleNamespace

from app.services import content_generation


def test_batch_generation_returns_four_grounded_formats(monkeypatch):
    article = SimpleNamespace(
        id=42,
        title="Nueva regulación de inteligencia artificial",
        summary="La autoridad publicó nuevas obligaciones.",
        full_text="La norma exige controles, documentación y evaluación de riesgos.",
        source_url="https://example.com/regulacion",
        classification_json={},
        verification_json={
            "facts": [
                {"claim": "La norma exige evaluación de riesgos", "supported": True}
            ]
        },
    )
    raw = json.dumps(
        {
            "pieces": [
                {
                    "format_type": format_type,
                    "title": f"Título {format_type}",
                    "body_text": f"Contenido {format_type}",
                    "body_json": (
                        {"slides": [{"title": "Uno", "text": "Texto"}]}
                        if format_type == "carousel"
                        else {}
                    ),
                    "key_claims": ["La norma exige controles"],
                }
                for format_type in content_generation.FORMATS
            ]
        }
    )
    monkeypatch.setattr(
        content_generation,
        "_call_model",
        lambda db, task_type, prompt: (raw, "test-model"),
    )

    drafts = content_generation._llm_package_drafts(object(), article, "es")

    assert set(drafts) == set(content_generation.FORMATS)
    assert all(article.source_url in draft["body_text"] for draft in drafts.values())
    assert all(
        draft["generation_mode"] == "gateway_batch" for draft in drafts.values()
    )
    assert drafts["carousel"]["body_json"]["slides"][0]["content"] == "Texto"
