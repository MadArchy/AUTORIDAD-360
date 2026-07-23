"""Orquestador: delega en LangGraph (API estable)."""

from __future__ import annotations

from typing import Literal

from app.agents.graphs import PIPELINE_STEPS
from app.agents.langgraph_runner import (
    describe_pipelines,
    list_agents,
    run_agent,
    run_pipeline,
)
from app.agents.roles import AGENTS, get_agent

PipelineMode = Literal["discover", "ingest", "article", "full"]

__all__ = [
    "AGENTS",
    "PIPELINE_STEPS",
    "PipelineMode",
    "describe_pipelines",
    "get_agent",
    "list_agents",
    "run_agent",
    "run_pipeline",
]
