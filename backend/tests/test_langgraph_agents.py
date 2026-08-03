"""Tests del orquestador LangGraph (tools y LLM mockeados)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agents.graph_nodes import route_after_review
from app.agents.graph_state import EditorialState, initial_editorial_state
from app.agents.langgraph_runner import describe_pipelines, list_agents, run_agent, run_pipeline


def test_list_agents_and_pipelines_engine():
    agents = list_agents()
    names = {a["name"] for a in agents}
    assert {
        "scout",
        "classifier",
        "verifier",
        "writer",
        "reviewer",
        "juan_editorial",
        "juan_ai_governance",
        "juan_ip_patents",
    } <= names
    pipes = describe_pipelines()
    assert pipes.get("engine") == "langgraph"
    assert "article" in pipes["modes"]
    assert "juan_practice" in pipes["modes"]
    assert pipes["steps"]["article"] == ["classifier", "verifier", "writer", "reviewer"]
    assert pipes["steps"]["juan_practice"] == [
        "juan_editorial",
        "juan_ai_governance",
        "juan_ip_patents",
    ]


def test_route_after_review_retry_and_done():
    state: EditorialState = {
        "artifacts": {"llm_critique": {"ok": False, "notes": "hype"}},
        "retry_write": 0,
        "max_write_retries": 1,
    }
    assert route_after_review(state) == "retry"
    state["retry_write"] = 1
    assert route_after_review(state) == "done"
    state["artifacts"] = {"llm_critique": {"ok": True}}
    state["retry_write"] = 0
    assert route_after_review(state) == "done"


@patch("app.agents.graph_nodes.fase5_ai.complete", return_value=("ok", {"model_used": "mock"}))
@patch("app.agents.graph_nodes.invoke_tool")
def test_run_agent_scout(mock_invoke, _mock_llm):
    mock_invoke.return_value = {"stats": {"found": 2}}
    db = MagicMock()
    db.info = {}
    result = run_agent(db, "scout", reason=False, limit=2)
    assert result["agent"] == "scout"
    assert result["ok"] is True
    assert result["artifacts"].get("scout_stats", {}).get("found") == 2
    mock_invoke.assert_called()
    assert mock_invoke.call_args[0][0] == "scout_web"


@patch("app.agents.graph_nodes.fase5_ai.complete")
@patch("app.agents.graph_nodes.invoke_tool")
def test_pipeline_article_happy_path(mock_invoke, mock_llm):
    mock_llm.side_effect = [
        ("pensando", {"model_used": "mock"}),
        ('{"ok": true, "notes": "bien"}', {"model_used": "mock"}),
    ]

    def _tool(name, db, **kwargs):
        if name == "classify_one":
            return {"article_id": 10, "status": "classified", "result": {}}
        if name == "verify_one":
            return {"article_id": 10, "status": "verified", "publishable": True, "result": {}}
        if name == "write_package":
            return {"package_id": 99, "status": "reviewing", "piece_ids": [1, 2], "formats": ["linkedin"]}
        if name == "review_package":
            return {
                "package_id": 99,
                "reviews": [{"piece_id": 1, "factual_passed": True, "brand_passed": True}],
            }
        raise AssertionError(f"tool inesperada: {name}")

    mock_invoke.side_effect = _tool
    db = MagicMock()
    db.info = {}
    result = run_pipeline(db, "article", article_id=10, reason=False)
    assert result["engine"] == "langgraph"
    assert result["ok"] is True
    assert result["artifacts"].get("package_id") == 99
    tools_used = [s.get("tool") for s in result["steps"] if s.get("tool") and s.get("tool") != "think"]
    assert "classify_one" in tools_used
    assert "verify_one" in tools_used
    assert "write_package" in tools_used
    assert "review_package" in tools_used


@patch("app.agents.graph_nodes.fase5_ai.complete", return_value=("x", {}))
@patch("app.agents.graph_nodes.invoke_tool")
def test_pipeline_article_stops_on_classify_soft_fail(mock_invoke, _mock_llm):
    mock_invoke.return_value = {
        "processed": 3,
        "classified": 0,
        "verified": 0,
        "errors": [{"error": "JSON inválido"}],
    }
    db = MagicMock()
    db.info = {}
    # ingest usa classify_batch
    result = run_pipeline(db, "ingest", limit=3, reason=False)
    assert result["ok"] is False
    assert any("Lote sin éxito" in (e or "") for e in (result.get("errors") or []))


@patch("app.agents.graph_nodes.fase5_ai.complete")
@patch("app.agents.graph_nodes.invoke_tool")
def test_pipeline_article_retries_writer_on_bad_critique(mock_invoke, mock_llm):
    write_calls = {"n": 0}

    def _llm(db, task_type="agent_plan", prompt=""):
        if task_type == "agent_critique":
            # Primera crítica falla → retry; segunda ok
            if write_calls["n"] <= 1:
                return ('{"ok": false, "notes": "hype"}', {"model_used": "mock"})
            return ('{"ok": true, "notes": "ok"}', {"model_used": "mock"})
        return ("think", {"model_used": "mock"})

    def _tool(name, db, **kwargs):
        if name == "classify_one":
            return {"article_id": 7, "status": "classified", "result": {}}
        if name == "verify_one":
            return {"article_id": 7, "status": "verified", "publishable": True, "result": {}}
        if name == "write_package":
            write_calls["n"] += 1
            return {
                "package_id": 50 + write_calls["n"],
                "status": "reviewing",
                "piece_ids": [write_calls["n"]],
                "formats": ["linkedin"],
            }
        if name == "review_package":
            return {"package_id": kwargs["package_id"], "reviews": [{"piece_id": 1, "factual_passed": True}]}
        raise AssertionError(name)

    mock_llm.side_effect = _llm
    mock_invoke.side_effect = _tool
    db = MagicMock()
    db.info = {}
    result = run_pipeline(db, "article", article_id=7, reason=False)
    assert write_calls["n"] >= 2
    assert result["artifacts"].get("package_id") is not None


def test_pipeline_article_requires_article_id():
    db = MagicMock()
    db.info = {}
    with pytest.raises(ValueError, match="article_id"):
        run_pipeline(db, "article", reason=False)


def test_structured_tools_are_langchain_native():
    from langchain_core.tools import StructuredTool
    from app.agents.tools import TOOL_CATALOG, build_structured_tools

    db = MagicMock()
    db.info = {}
    tools = build_structured_tools(db)
    assert set(tools) == set(TOOL_CATALOG)
    for name, tool in tools.items():
        assert isinstance(tool, StructuredTool)
        assert tool.name == name
        assert tool.description


def test_structured_tool_validates_required_args():
    from app.agents.tools import build_structured_tools

    db = MagicMock()
    db.info = {}
    tools = build_structured_tools(db)
    with pytest.raises(Exception):
        tools["classify_one"].invoke({})
