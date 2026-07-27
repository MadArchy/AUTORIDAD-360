"""Grafos LangGraph del flujo editorial."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.graph_nodes import bump_write_retry, make_agent_node, route_after_review
from app.agents.graph_state import EditorialState

PipelineMode = Literal["discover", "ingest", "article", "full", "trends"]

PIPELINE_STEPS: dict[str, list[str]] = {
    "discover": ["scout", "trend_ad_advisor"],
    "ingest": ["classifier"],
    "article": ["classifier", "verifier", "writer", "reviewer"],
    "full": ["scout", "classifier"],
    "trends": ["trend_ad_advisor"],
}

AGENT_NAMES = ("scout", "classifier", "verifier", "writer", "reviewer", "trend_ad_advisor")


def _route_if_ok(state: EditorialState) -> str:
    return "continue" if state.get("ok", True) else "stop"


def build_pipeline_graph(db: Session, mode: PipelineMode):
    """Compila el grafo del modo de pipeline."""
    if mode not in PIPELINE_STEPS:
        raise ValueError(f"mode inválido: {mode}. Usa {list(PIPELINE_STEPS)}")

    graph = StateGraph(EditorialState)

    if mode == "discover":
        graph.add_node("scout", make_agent_node(db, "scout"))
        graph.add_node("trend_ad_advisor", make_agent_node(db, "trend_ad_advisor"))
        graph.add_edge(START, "scout")
        graph.add_conditional_edges(
            "scout",
            _route_if_ok,
            {"continue": "trend_ad_advisor", "stop": "trend_ad_advisor"},
        )
        graph.add_edge("trend_ad_advisor", END)
        return graph.compile()

    if mode == "trends":
        graph.add_node("trend_ad_advisor", make_agent_node(db, "trend_ad_advisor"))
        graph.add_edge(START, "trend_ad_advisor")
        graph.add_edge("trend_ad_advisor", END)
        return graph.compile()

    if mode == "ingest":
        graph.add_node("classifier", make_agent_node(db, "classifier"))
        graph.add_edge(START, "classifier")
        graph.add_edge("classifier", END)
        return graph.compile()

    if mode == "full":
        graph.add_node("scout", make_agent_node(db, "scout"))
        graph.add_node("classifier", make_agent_node(db, "classifier"))
        graph.add_edge(START, "scout")
        graph.add_conditional_edges(
            "scout",
            _route_if_ok,
            {"continue": "classifier", "stop": END},
        )
        graph.add_edge("classifier", END)
        return graph.compile()

    # article: classify → verify → write → review → (retry writer?)
    graph.add_node("classifier", make_agent_node(db, "classifier"))
    graph.add_node("verifier", make_agent_node(db, "verifier"))
    graph.add_node("writer", make_agent_node(db, "writer"))
    graph.add_node("reviewer", make_agent_node(db, "reviewer"))
    graph.add_node("bump_write_retry", bump_write_retry)

    graph.add_edge(START, "classifier")
    graph.add_conditional_edges(
        "classifier",
        _route_if_ok,
        {"continue": "verifier", "stop": END},
    )
    graph.add_conditional_edges(
        "verifier",
        _route_if_ok,
        {"continue": "writer", "stop": END},
    )
    graph.add_conditional_edges(
        "writer",
        _route_if_ok,
        {"continue": "reviewer", "stop": END},
    )
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,
        {
            "retry": "bump_write_retry",
            "done": END,
        },
    )
    graph.add_edge("bump_write_retry", "writer")
    return graph.compile()


def build_single_agent_graph(db: Session, name: str):
    """Grafo de un solo nodo para POST /agents/{name}/run."""
    key = name.strip().lower()
    if key not in AGENT_NAMES:
        raise KeyError(f"Agente desconocido: {name}. Disponibles: {list(AGENT_NAMES)}")
    graph = StateGraph(EditorialState)
    graph.add_node(key, make_agent_node(db, key))
    graph.add_edge(START, key)
    graph.add_edge(key, END)
    return graph.compile()


def describe_pipeline_modes() -> dict[str, Any]:
    return {
        "engine": "langgraph",
        "modes": {
            "discover": "Scout tipologías del día + notas/tendencias orgánicas",
            "ingest": "Classifier/Verifier en lote (artículos collected)",
            "article": "Clasificar → Verificar → Redactar → Revisar (LangGraph; reintento writer si critique falla)",
            "full": "Scout + lote de clasificación/verificación",
            "trends": "Solo advisor de tendencias y notas para redes (DDG news del día)",
        },
        "steps": PIPELINE_STEPS,
    }
