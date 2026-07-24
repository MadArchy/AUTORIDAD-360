"""Tests para el servicio de Copiloto IA de Autoridad 360."""

import pytest
from types import SimpleNamespace
from app.services import ai_copilot_service
from app.models.editorial import NewsArticle, BlogPost


def test_refine_article_content(monkeypatch):
    article = SimpleNamespace(
        id=101,
        title="Nueva Ley de IA",
        source_name="Boletín Oficial",
        url="https://example.com/law",
        full_text="Texto legal original sobre la inteligencia artificial.",
        summary="Resumen de la ley.",
    )

    def mock_query(model):
        class MockQuery:
            def filter_by(self, **kwargs):
                return self
            def first(self):
                return article
        return MockQuery()

    class MockDB:
        def query(self, model):
            return mock_query(model)
        def add(self, item):
            pass
        def flush(self):
            pass

    monkeypatch.setattr(
        ai_copilot_service,
        "_call_model",
        lambda db, task_type, prompt, **kwargs: ("Texto refinado con enfoque jurídico.", "test-model"),
    )
    monkeypatch.setattr(ai_copilot_service, "log_audit", lambda *args, **kwargs: None)

    res = ai_copilot_service.refine_article_content(
        MockDB(),
        article_id=101,
        instruction="Reescribir con tono más jurídico",
        target_field="full_text",
    )

    assert res["article_id"] == 101
    assert res["target_field"] == "full_text"
    assert res["refined_content"] == "Texto refinado con enfoque jurídico."
    assert res["model_used"] == "test-model"


def test_refine_blog_post_content(monkeypatch):
    post = SimpleNamespace(
        id=202,
        title="Post sobre IA en Abogacía",
        body_markdown="# Título\nContenido de prueba.",
        summary="Resumen del post.",
    )

    def mock_query(model):
        class MockQuery:
            def filter_by(self, **kwargs):
                return self
            def first(self):
                return post
        return MockQuery()

    class MockDB:
        def query(self, model):
            return mock_query(model)
        def add(self, item):
            pass
        def flush(self):
            pass

    monkeypatch.setattr(
        ai_copilot_service,
        "_call_model",
        lambda db, task_type, prompt, **kwargs: ("# Título Mejorado\nContenido refinado SEO.", "test-model"),
    )
    monkeypatch.setattr(ai_copilot_service, "log_audit", lambda *args, **kwargs: None)

    res = ai_copilot_service.refine_blog_post_content(
        MockDB(),
        post_id=202,
        instruction="Optimizar para SEO",
        target_field="body_markdown",
    )

    assert res["post_id"] == 202
    assert res["refined_content"] == "# Título Mejorado\nContenido refinado SEO."
