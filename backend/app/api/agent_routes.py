"""API de agentes editoriales reales."""

from __future__ import annotations

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
    mode: Literal["discover", "ingest", "article", "full"] = "article"
    article_id: int | None = None
    limit: int = Field(default=5, ge=1, le=30)
    languages: list[str] = Field(default_factory=lambda: ["es"])
    prefer_llm: bool = True
    query: str | None = None
    reason: bool = True


@router.get("")
def get_agents(
    ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, Any]:
    require_roles(ctx, *_AGENT_STAFF)
    return {"agents": list_agents(), "pipelines": describe_pipelines()}


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
