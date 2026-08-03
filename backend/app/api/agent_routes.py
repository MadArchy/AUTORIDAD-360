"""API de agentes editoriales reales."""

from __future__ import annotations

import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import describe_pipelines, list_agents, run_agent, run_pipeline
from app.db.database import get_db
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

_AGENT_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "analyst",
    "community_manager",
)
_AGENT_RUNNERS = ("agency_admin", "strategist", "writer", "editor", "analyst")


class AgentRunRequest(BaseModel):
    goal: str | None = None
    article_id: int | None = None
    package_id: int | None = None
    limit: int = Field(default=5, ge=1, le=30)
    languages: list[str] = Field(default_factory=lambda: ["es"])
    prefer_llm: bool = True
    query: str | None = None
    reason: bool = True


class PipelineRunRequest(BaseModel):
    mode: Literal[
        "discover", "ingest", "article", "full", "trends", "juan_practice"
    ] = "article"
    article_id: int | None = None
    limit: int = Field(default=5, ge=1, le=30)
    languages: list[str] = Field(default_factory=lambda: ["es"])
    prefer_llm: bool = True
    query: str | None = None
    reason: bool = True


class AutoCycleRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)
    include_juan: bool = True
    reason: bool = False


@router.get("")
def get_agents(
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    require_roles(ctx, *_AGENT_STAFF)
    from app.agents.runtime import describe_priority_catalog, get_agent_board

    board = get_agent_board(ctx.org_id)
    return {
        "agents": list_agents(),
        "pipelines": describe_pipelines(),
        "priority": describe_priority_catalog(),
        "board": board,
    }


@router.get("/status")
def get_agents_status(
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Tablero en vivo: quién está activo y qué función ejecuta."""
    require_roles(ctx, *_AGENT_STAFF)
    from app.agents.runtime import get_agent_board

    return get_agent_board(ctx.org_id)


@router.post("/auto/run")
def post_auto_cycle(
    body: AutoCycleRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    """Encola ciclo automático por prioridad (Celery) o lo corre sync si falla encolar."""
    require_roles(ctx, *_AGENT_RUNNERS)
    from app.services.job_runner import enqueue_job
    from app.tasks import run_agent_priority_cycle_task

    try:
        job = enqueue_job(
            db,
            job_name="agent_auto_cycle",
            celery_task=run_agent_priority_cycle_task,
            idempotency_key=f"agent-auto:{ctx.org_id}:{int(time.time())}",
            organization_id=ctx.org_id,
            task_kwargs={
                "organization_id": ctx.org_id,
                "limit": body.limit,
                "include_juan": body.include_juan,
                "reason": body.reason,
            },
        )
        return {
            "ok": True,
            "queued": True,
            "job": {
                "id": job.id,
                "status": job.status,
                "job_name": job.job_name,
            },
            "message": "Ciclo automático encolado. Mira el tablero de estado.",
        }
    except Exception as exc:  # noqa: BLE001
        # Fallback sync (dev / sin worker)
        from app.services.agent_auto_cycle import run_priority_cycle

        try:
            result = run_priority_cycle(
                db,
                organization_id=ctx.org_id,
                limit=body.limit,
                include_juan=body.include_juan,
                reason=body.reason,
            )
            return {"ok": result.get("ok"), "queued": False, "sync": True, **result}
        except Exception as inner:  # noqa: BLE001
            raise HTTPException(
                status_code=500, detail=f"Auto cycle falló: {exc}; sync: {inner}"[:500]
            ) from inner


@router.post("/pipeline/run")
def post_run_pipeline(
    body: PipelineRunRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    require_roles(ctx, *_AGENT_RUNNERS)
    try:
        return run_pipeline(
            db,
            body.mode,
            article_id=body.article_id,
            limit=body.limit,
            languages=body.languages,
            prefer_llm=body.prefer_llm,
            query=body.query,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc


@router.get("/{name}")
def get_agent_detail(
    name: str,
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    require_roles(ctx, *_AGENT_STAFF)
    from app.agents.roles import get_agent

    try:
        return get_agent(name).describe()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{name}/run")
def post_run_agent(
    name: str,
    body: AgentRunRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    require_roles(ctx, *_AGENT_RUNNERS)
    try:
        return run_agent(
            db,
            name,
            goal=body.goal,
            article_id=body.article_id,
            package_id=body.package_id,
            limit=body.limit,
            languages=body.languages,
            prefer_llm=body.prefer_llm,
            query=body.query,
            reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)[:500]) from exc
