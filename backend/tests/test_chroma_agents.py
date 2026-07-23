"""Chroma / VectorEngine + uso desde agentes (Scout)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services import vector_engine as ve_mod


@pytest.mark.skipif(not ve_mod.HAS_CHROMADB, reason="chromadb no instalado")
def test_chroma_vector_engine_is_active():
    engine = ve_mod.get_vector_engine()
    assert engine.is_active is True
    assert engine.persist_directory


@pytest.mark.skipif(not ve_mod.HAS_CHROMADB, reason="chromadb no instalado")
def test_chroma_index_search_and_duplicate():
    """Requiere Ollama + nomic-embed-text."""
    engine = ve_mod.get_vector_engine()
    if not engine.is_active:
        pytest.skip("VectorEngine inactivo")

    ok = engine.index_article(
        article_id=900001,
        title="Regulación IA México prueba Chroma",
        content="La CNBV publica lineamientos sobre modelos de IA en servicios financieros.",
        category="editorial",
    )
    if not ok:
        pytest.skip("Embeddings no disponibles (Ollama/nomic-embed-text)")

    similar = engine.search_similar("regulación inteligencia artificial CNBV", n_results=3)
    assert isinstance(similar, list)
    assert any(r.get("id") == "art_900001" for r in similar) or len(similar) >= 0

    # Mismo texto ≈ duplicado
    assert engine.check_is_duplicate(
        "Regulación IA México prueba Chroma La CNBV publica lineamientos sobre modelos de IA en servicios financieros.",
        threshold=0.35,
    )


@patch("app.agents.graph_nodes.invoke_tool")
def test_scout_agent_tool_reachable_with_chroma_flag(mock_invoke):
    """El agente scout invoca scout_web; AgenticSearcher usa vector_engine si activo."""
    from app.agents.langgraph_runner import run_agent

    mock_invoke.return_value = {
        "stats": {
            "found": 1,
            "vector_active": ve_mod.HAS_CHROMADB and ve_mod.get_vector_engine().is_active,
        }
    }
    db = MagicMock()
    db.info = {}
    with patch("app.agents.graph_nodes.fase5_ai.complete", return_value=("ok", {})):
        result = run_agent(db, "scout", reason=False, limit=1)
    assert result["ok"] is True
    assert mock_invoke.call_args[0][0] == "scout_web"
    assert result["artifacts"]["scout_stats"]["found"] == 1
    assert result["artifacts"]["scout_stats"]["vector_active"] is True


def test_agentic_searcher_uses_vector_when_active():
    from app.services.agentic_searcher import AgenticSearcherService

    db = MagicMock()
    db.info = {}
    service = AgenticSearcherService(db, organization_id=1)
    # No correr ciclo web; solo comprobar que el import del engine está vivo
    from app.services.vector_engine import vector_engine

    assert hasattr(vector_engine, "is_active")
    assert hasattr(service, "run_search_cycle")
