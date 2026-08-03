"""Runner LangGraph: mantiene contrato de respuesta de agentes/pipelines."""

from __future__ import annotations

import time
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agents.context import new_run_id
from app.agents.graph_state import initial_editorial_state
from app.agents.graphs import (
    AGENT_NAMES,
    PIPELINE_STEPS,
    build_pipeline_graph,
    build_single_agent_graph,
    describe_pipeline_modes,
)
from app.agents.roles import AGENTS

PipelineMode = Literal["discover", "ingest", "article", "full", "trends"]


def list_agents() -> list[dict[str, Any]]:
    return [a.describe() for a in AGENTS.values()]


def describe_pipelines() -> dict[str, Any]:
    return describe_pipeline_modes()


def _org_id(db: Session) -> int | None:
    return db.info.get("organization_id")


def _agent_result_slice(
    *,
    run_id: str,
    agent: str,
    state: dict[str, Any],
    started_at: str,
    finished_at: str,
    duration_ms: int,
) -> dict[str, Any]:
    steps = [
        s
        for s in (state.get("steps") or [])
        if s.get("agent") == agent
    ]
    return {
        "run_id": run_id,
        "agent": agent,
        "ok": bool(state.get("ok", True)),
        "summary": state.get("summary") or "sin pasos",
        "steps": steps,
        "artifacts": dict(state.get("artifacts") or {}),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
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
    key = name.strip().lower()
    if key not in AGENT_NAMES:
        raise KeyError(f"Agente desconocido: {name}. Disponibles: {list(AGENT_NAMES)}")

    run_id = new_run_id()
    started = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    org_id = _org_id(db)
    if org_id is not None:
        db.info["organization_id"] = org_id

    state = initial_editorial_state(
        goal=goal or f"Ejecutar agente {key}",
        article_id=article_id,
        package_id=package_id,
        limit=limit,
        languages=languages,
        prefer_llm=prefer_llm,
        query=query,
        reason=reason,
        organization_id=org_id,
        run_id=run_id,
        agent=key,
    )
    graph = build_single_agent_graph(db, key)
    final = graph.invoke(state)
    finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    duration_ms = int((time.perf_counter() - started) * 1000)
    return _agent_result_slice(
        run_id=run_id,
        agent=key,
        state=final,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
    )


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
    if mode in {"article", "juan_practice"} and not article_id:
        raise ValueError(f"pipeline {mode} requiere article_id")

    run_id = new_run_id()
    started = time.perf_counter()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    org_id = _org_id(db)
    if org_id is not None:
        db.info["organization_id"] = org_id

    state = initial_editorial_state(
        goal=f"Pipeline editorial mode={mode}",
        article_id=article_id,
        limit=limit,
        languages=languages,
        prefer_llm=prefer_llm,
        query=query,
        reason=reason,
        organization_id=org_id,
        run_id=run_id,
        agent="pipeline",
        max_write_retries=1,
    )
    graph = build_pipeline_graph(db, mode)
    final = graph.invoke(state)
    finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    duration_ms = int((time.perf_counter() - started) * 1000)

    # Compat: agent_results por agente del modo (pasos filtrados)
    agent_results: list[dict[str, Any]] = []
    for agent_name in PIPELINE_STEPS[mode]:
        agent_results.append(
            _agent_result_slice(
                run_id=run_id,
                agent=agent_name,
                state=final,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
            )
        )

    return {
        "run_id": run_id,
        "mode": mode,
        "ok": bool(final.get("ok", True)),
        "engine": "langgraph",
        "agents": list(PIPELINE_STEPS[mode]),
        "agent_results": agent_results,
        "artifacts": dict(final.get("artifacts") or {}),
        "steps": list(final.get("steps") or []),
        "errors": list(final.get("errors") or []),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
    }
