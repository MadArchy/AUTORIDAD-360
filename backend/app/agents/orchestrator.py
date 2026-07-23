"""Orquestador: encadena agentes reales sobre el flujo editorial."""

from __future__ import annotations

import time
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agents.context import AgentContext, new_run_id
from app.agents.roles import AGENTS, get_agent

PipelineMode = Literal["discover", "ingest", "article", "full"]

PIPELINE_STEPS: dict[str, list[str]] = {
    "discover": ["scout"],
    "ingest": ["classifier"],  # classify_batch ya verifica
    "article": ["classifier", "verifier", "writer", "reviewer"],
    "full": ["scout", "classifier"],
}


def list_agents() -> list[dict[str, Any]]:
    return [a.describe() for a in AGENTS.values()]


def describe_pipelines() -> dict[str, Any]:
    return {
        "modes": {
            "discover": "Solo Scout (búsqueda web + evaluación IA)",
            "ingest": "Classifier/Verifier en lote (artículos collected)",
            "article": "Clasificar → Verificar → Redactar → Revisar (un article_id)",
            "full": "Scout + lote de clasificación/verificación",
        },
        "steps": PIPELINE_STEPS,
    }


def run_agent(
    db: Session,
    name: str,
    *,
    goal: str | None = None,
    article_id: int | None = None,
    package_id: int | None = None,
    limit: int = 5,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
    query: str | None = None,
    reason: bool = True,
) -> dict[str, Any]:
    agent = get_agent(name)
    ctx = AgentContext(
        goal=goal or f"Ejecutar agente {agent.name}",
        article_id=article_id,
        limit=limit,
        languages=languages or ["es"],
        prefer_llm=prefer_llm,
        query=query,
        extras={"package_id": package_id} if package_id else {},
    )
    if package_id:
        ctx.set_artifact("package_id", package_id)
    result = agent.run(db, ctx, reason=reason)
    return result.to_dict()


def run_pipeline(
    db: Session,
    mode: PipelineMode = "article",
    *,
    article_id: int | None = None,
    limit: int = 5,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
    query: str | None = None,
    reason: bool = True,
) -> dict[str, Any]:
    if mode not in PIPELINE_STEPS:
        raise ValueError(f"mode inválido: {mode}. Usa {list(PIPELINE_STEPS)}")
    if mode == "article" and not article_id:
        raise ValueError("pipeline article requiere article_id")

    run_id = new_run_id()
    started = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    ctx = AgentContext(
        goal=f"Pipeline editorial mode={mode}",
        article_id=article_id,
        limit=limit,
        languages=languages or ["es"],
        prefer_llm=prefer_llm,
        query=query,
    )

    agent_results: list[dict[str, Any]] = []
    ok = True
    for agent_name in PIPELINE_STEPS[mode]:
        agent = get_agent(agent_name)
        # Tras writer, reviewer usa package_id del artifact
        result = agent.run(db, ctx, reason=reason)
        agent_results.append(result.to_dict())
        if not result.ok:
            ok = False
            break
        # Mantener article_id si el batch no lo fija
        if ctx.artifacts.get("article_id"):
            ctx.article_id = int(ctx.artifacts["article_id"])

    finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {
        "run_id": run_id,
        "mode": mode,
        "ok": ok,
        "agents": [s for s in PIPELINE_STEPS[mode]],
        "agent_results": agent_results,
        "artifacts": ctx.artifacts,
        "steps": [
            {
                "agent": s.agent,
                "tool": s.tool,
                "status": s.status,
                "detail": s.detail,
                "data": s.data,
                "at": s.at,
            }
            for s in ctx.steps
        ],
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": int((time.perf_counter() - started) * 1000),
    }
