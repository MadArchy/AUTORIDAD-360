"""Estado tipado del grafo editorial LangGraph."""

from __future__ import annotations

from typing import Any, TypedDict


class EditorialState(TypedDict, total=False):
    goal: str
    article_id: int | None
    package_id: int | None
    limit: int
    languages: list[str]
    prefer_llm: bool
    query: str | None
    reason: bool
    organization_id: int | None
    steps: list[dict[str, Any]]
    artifacts: dict[str, Any]
    errors: list[str]
    ok: bool
    retry_write: int
    max_write_retries: int
    # Metadatos de corrida (rellena el runner)
    run_id: str
    agent: str
    summary: str


def initial_editorial_state(
    *,
    goal: str,
    article_id: int | None = None,
    package_id: int | None = None,
    limit: int = 5,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
    query: str | None = None,
    reason: bool = True,
    organization_id: int | None = None,
    max_write_retries: int = 1,
    run_id: str = "",
    agent: str = "pipeline",
) -> EditorialState:
    artifacts: dict[str, Any] = {}
    if package_id:
        artifacts["package_id"] = package_id
    if article_id:
        artifacts["article_id"] = article_id
    return EditorialState(
        goal=goal,
        article_id=article_id,
        package_id=package_id,
        limit=limit,
        languages=languages or ["es"],
        prefer_llm=prefer_llm,
        query=query,
        reason=reason,
        organization_id=organization_id,
        steps=[],
        artifacts=artifacts,
        errors=[],
        ok=True,
        retry_write=0,
        max_write_retries=max_write_retries,
        run_id=run_id,
        agent=agent,
        summary="",
    )
