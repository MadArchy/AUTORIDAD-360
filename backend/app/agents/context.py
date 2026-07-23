"""Contexto compartido y resultados de ejecución de agentes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentStep:
    agent: str
    tool: str | None
    status: str  # ok | skip | error | think
    detail: str
    data: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=lambda: _utcnow().isoformat())


@dataclass
class AgentContext:
    """Memoria de corrida compartida entre agentes."""

    goal: str
    article_id: int | None = None
    limit: int = 5
    languages: list[str] = field(default_factory=lambda: ["es"])
    prefer_llm: bool = True
    query: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)
    steps: list[AgentStep] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def log(
        self,
        agent: str,
        *,
        tool: str | None = None,
        status: str = "ok",
        detail: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        self.steps.append(
            AgentStep(
                agent=agent,
                tool=tool,
                status=status,
                detail=detail[:800],
                data=data or {},
            )
        )

    def set_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value


@dataclass
class AgentRunResult:
    run_id: str
    agent: str
    ok: bool
    summary: str
    steps: list[dict[str, Any]]
    artifacts: dict[str, Any]
    started_at: str
    finished_at: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent": self.agent,
            "ok": self.ok,
            "summary": self.summary,
            "steps": self.steps,
            "artifacts": self.artifacts,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
        }


def new_run_id() -> str:
    return uuid4().hex[:12]
