import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import NewsArticle, NewsCategory, BlogPost, MultiNewsSynthesis
from app.services.multi_news_synthesis import suggest_central_focus, generate_centralized_synthesis


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_suggest_central_focus_and_synthesis(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.multi_news_synthesis.call_llm",
        lambda prompt, system_prompt="", db=None: (
            '{"suggested_focus": "Impacto de las nuevas normativas de IA y privacidad.", '
            '"title": "Análisis Consolidado: Gobernanza de IA 2026", '
            '"seo_description": "Síntesis de normativas de IA", '
            '"content_html": "<p>Contenido sintetizado de prueba.</p>"}'
        )
    )

    # 1. Crear categoría de prueba
    cat = NewsCategory(slug="tech-test", name="Tech Test", rss_url="http://test.local/rss")
    db_session.add(cat)
    db_session.flush()

    # 2. Crear 2 noticias de prueba
    art1 = NewsArticle(
        category_id=cat.id,
        title="Nueva Regulación de IA Transfronteriza 2026",
        source_url="http://test.local/news1",
        source_name="Tech Journal",
        full_text="Las empresas deberán implementar marcos de gobernanza y privacidad para algoritmos.",
        content_hash="hash_test_1"
    )
    art2 = NewsArticle(
        category_id=cat.id,
        title="Impacto del Cumplimiento Algorítmico en PyMEs",
        source_url="http://test.local/news2",
        source_name="Legal Tech Today",
        full_text="El costo de auditorías de IA impulsará nuevos servicios de consultoría legal especializada.",
        content_hash="hash_test_2"
    )
    db_session.add_all([art1, art2])
    db_session.commit()

    article_ids = [art1.id, art2.id]

    # 3. Probar sugerencia de foco único
    suggestion = suggest_central_focus(db_session, article_ids)
    assert "suggested_focus" in suggestion
    assert len(suggestion["suggested_focus"]) > 0

    # 4. Probar generación de artículo consolidado
    foco = "Estrategias de cumplimiento legal y gobernanza de IA para mantener la competitividad empresarial."
    res = generate_centralized_synthesis(
        db=db_session,
        article_ids=article_ids,
        central_focus=foco,
        author_name="Juan Vásquez Demo"
    )

    assert "synthesis_id" in res
    assert "blog_post_id" in res
    assert res["status"] == "pending"

    # Verificación en BD
    blog = db_session.query(BlogPost).get(res["blog_post_id"])
    assert blog is not None
    assert "Fuentes Consultadas" in blog.content_html
    assert "Tech Journal" in blog.content_html
    assert "Legal Tech Today" in blog.content_html

    synthesis = db_session.query(MultiNewsSynthesis).get(res["synthesis_id"])
    assert synthesis is not None
    assert synthesis.central_focus == foco
    assert len(synthesis.source_article_ids) == 2

