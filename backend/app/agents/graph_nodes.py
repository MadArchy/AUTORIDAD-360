"""Nodos LangGraph: roles editoriales que invocan tools existentes + fase5_ai."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.agents.base import extract_json_object
from app.agents.graph_state import EditorialState
from app.agents.roles import AGENTS
from app.agents.tools import TOOL_CATALOG, invoke_tool
from app.services import fase5_ai

NodeFn = Callable[[EditorialState], dict[str, Any]]


def _batch_soft_fail(data: dict[str, Any]) -> str | None:
    """Detecta lotes que corren pero no producen resultado útil."""
    if not isinstance(data, dict):
        return None
    errors = data.get("errors")
    processed = data.get("processed")
    if isinstance(errors, list) and processed is not None:
        classified = int(data.get("classified") or 0)
        verified = int(data.get("verified") or 0)
        if int(processed) > 0 and classified == 0 and verified == 0 and errors:
            first = errors[0] if errors else {}
            msg = first.get("error") if isinstance(first, dict) else str(first)
            return f"Lote sin éxito: {msg or 'errores en clasificación'}"
        if int(processed) > 0 and errors and verified == 0 and classified > 0:
            first = errors[0] if errors else {}
            msg = first.get("error") if isinstance(first, dict) else str(first)
            return f"Clasificado pero verificación falló: {msg or 'JSON inválido'}"
    return None


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_preview(data: dict[str, Any], limit: int = 1200) -> dict[str, Any]:
    raw = json.dumps(data, default=str)
    if len(raw) <= limit:
        return data
    return {"preview": raw[:limit] + "…"}


def _append_step(
    steps: list[dict[str, Any]],
    agent: str,
    *,
    tool: str | None = None,
    status: str = "ok",
    detail: str = "",
    data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    next_steps = list(steps or [])
    next_steps.append(
        {
            "agent": agent,
            "tool": tool,
            "status": status,
            "detail": (detail or "")[:800],
            "data": data or {},
            "at": _utcnow_iso(),
        }
    )
    return next_steps


def _think(db: Session, agent_name: str, state: EditorialState) -> tuple[list[dict[str, Any]], str | None]:
    steps = list(state.get("steps") or [])
    if not state.get("reason", True):
        return steps, None
    agent = AGENTS.get(agent_name)
    role = agent.role if agent else agent_name
    tools = agent.tools if agent else []
    tool_lines = "\n".join(
        f"- {t}: {TOOL_CATALOG.get(t, {}).get('description', '')}" for t in tools
    )
    prompt = (
        f"Eres el agente «{agent_name}» ({role}) en Autoridad 360.\n"
        f"Objetivo de la corrida: {state.get('goal')}\n"
        f"article_id={state.get('article_id')} limit={state.get('limit')}\n"
        f"Herramientas disponibles:\n{tool_lines}\n\n"
        "Responde en 2-3 frases: qué vas a hacer y por qué. Sin JSON."
    )
    try:
        text, meta = fase5_ai.complete(db, task_type=agent.task_type if agent else "agent_plan", prompt=prompt)
        thought = (text or "").strip()[:600]
        steps = _append_step(
            steps,
            agent_name,
            tool="think",
            status="think",
            detail=thought or "sin texto",
            data={"model": meta.get("model_used"), "latency_ms": meta.get("latency_ms")},
        )
        return steps, thought
    except Exception as exc:  # noqa: BLE001
        steps = _append_step(
            steps,
            agent_name,
            tool="think",
            status="skip",
            detail=f"Razonamiento omitido: {exc}",
        )
        return steps, None


def _plan_tools(agent_name: str, state: EditorialState) -> list[tuple[str, dict[str, Any]]]:
    article_id = state.get("article_id")
    limit = int(state.get("limit") or 5)
    languages = list(state.get("languages") or ["es"])
    prefer_llm = bool(state.get("prefer_llm", True))
    query = state.get("query")
    artifacts = dict(state.get("artifacts") or {})

    if agent_name == "scout":
        kwargs: dict[str, Any] = {
            "max_queries": min(14, max(6, limit * 2)),
            "max_results_per_query": 4,
            "max_priority": 11,
            "max_age_hours": 36,
        }
        if query:
            kwargs["queries"] = [query]
        return [("scout_web", kwargs)]

    if agent_name == "trend_ad_advisor":
        kwargs = {
            "max_queries": min(14, max(8, limit * 2)),
            "slug": (state.get("extras") or {}).get("slug") or "juan-vasquez",
        }
        return [("trend_ad_notes", kwargs)]

    if agent_name == "classifier":
        if article_id:
            return [("classify_one", {"article_id": article_id})]
        return [("classify_batch", {"limit": limit})]

    if agent_name == "verifier":
        if article_id:
            return [("verify_one", {"article_id": article_id})]
        return [("classify_batch", {"limit": limit})]

    if agent_name == "writer":
        if not article_id:
            raise ValueError("writer requiere article_id de un artículo verificado")
        return [
            (
                "write_package",
                {
                    "article_id": article_id,
                    "languages": languages,
                    "prefer_llm": prefer_llm,
                },
            )
        ]

    if agent_name == "juan_editorial":
        if not article_id:
            raise ValueError("juan_editorial requiere article_id de un artículo verificado")
        return [
            (
                "draft_juan_editorial",
                {
                    "article_id": article_id,
                    "languages": languages,
                    "prefer_llm": prefer_llm,
                },
            )
        ]

    if agent_name == "juan_ai_governance":
        kwargs: dict[str, Any] = {}
        if article_id:
            kwargs["article_id"] = article_id
        if query:
            kwargs["topic"] = query
        if not kwargs.get("article_id") and not kwargs.get("topic"):
            raise ValueError("juan_ai_governance requiere article_id o query")
        return [("draft_ai_governance_brief", kwargs)]

    if agent_name == "juan_ip_patents":
        kwargs = {}
        if article_id:
            kwargs["article_id"] = article_id
        if query:
            kwargs["topic"] = query
        if not kwargs.get("article_id") and not kwargs.get("topic"):
            raise ValueError("juan_ip_patents requiere article_id o query")
        return [("draft_ip_patent_brief", kwargs)]

    if agent_name == "reviewer":
        package_id = artifacts.get("package_id") or state.get("package_id")
        if not package_id:
            raise ValueError("reviewer requiere package_id (genera primero con writer)")
        return [("review_package", {"package_id": int(package_id)})]

    raise ValueError(f"Agente desconocido en grafo: {agent_name}")


def _apply_tool_artifacts(artifacts: dict[str, Any], tool_name: str, data: dict[str, Any]) -> None:
    if tool_name in ("write_package", "draft_juan_editorial") and data.get("package_id"):
        artifacts["package_id"] = data["package_id"]
        artifacts["piece_ids"] = data.get("piece_ids", [])
    if tool_name == "scout_web":
        artifacts["scout_stats"] = data.get("stats")
    if tool_name == "trend_ad_notes":
        notes = data.get("notes") if isinstance(data.get("notes"), dict) else data
        artifacts["trend_notes"] = {
            "generated_at": (notes or {}).get("generated_at"),
            "trends_count": data.get("trends_count") or len((notes or {}).get("trends") or []),
            "hits_count": data.get("hits_count") or ((notes or {}).get("meta") or {}).get("hits_count"),
        }
    if tool_name in ("classify_one", "verify_one") and data.get("article_id"):
        artifacts["article_id"] = data["article_id"]
        artifacts["article_status"] = data.get("status")
    if tool_name == "classify_batch":
        artifacts["batch"] = data
    if tool_name == "review_package":
        artifacts["reviews"] = data.get("reviews")
    if tool_name == "draft_ai_governance_brief":
        artifacts["ai_governance_brief"] = {
            "topic": data.get("topic"),
            "article_id": data.get("article_id"),
            "model_used": data.get("model_used"),
            "brief_preview": (data.get("brief_markdown") or "")[:500],
        }
    if tool_name == "draft_ip_patent_brief":
        artifacts["ip_patent_brief"] = {
            "topic": data.get("topic"),
            "article_id": data.get("article_id"),
            "model_used": data.get("model_used"),
            "brief_preview": (data.get("brief_markdown") or "")[:500],
        }


def _run_agent_node(db: Session, agent_name: str, state: EditorialState) -> dict[str, Any]:
    from app.agents.runtime import set_agent_status

    steps, _ = _think(db, agent_name, state)
    artifacts = dict(state.get("artifacts") or {})
    errors = list(state.get("errors") or [])
    ok = bool(state.get("ok", True))
    article_id = state.get("article_id")
    org_id = state.get("organization_id")
    summary_parts: list[str] = []
    set_agent_status(
        agent_name,
        organization_id=org_id,
        status="running",
        current_step="plan",
        run_id=state.get("run_id"),
        article_id=article_id,
        error=None,
    )

    try:
        planned = _plan_tools(agent_name, state)
    except Exception as exc:  # noqa: BLE001
        steps = _append_step(steps, agent_name, status="error", detail=str(exc)[:500])
        errors.append(str(exc)[:500])
        set_agent_status(
            agent_name,
            organization_id=org_id,
            status="failed",
            error=str(exc)[:400],
            ok=False,
            article_id=article_id,
        )
        return {
            "steps": steps,
            "artifacts": artifacts,
            "errors": errors,
            "ok": False,
            "summary": f"plan: {exc}",
            "article_id": article_id,
        }

    for tool_name, kwargs in planned:
        set_agent_status(
            agent_name,
            organization_id=org_id,
            status="running",
            current_step=tool_name,
            current_tool=tool_name,
            article_id=article_id or kwargs.get("article_id"),
            run_id=state.get("run_id"),
        )
        try:
            data = invoke_tool(tool_name, db, **kwargs)
            soft_fail = _batch_soft_fail(data)
            status = "error" if soft_fail else "ok"
            if soft_fail:
                ok = False
            steps = _append_step(
                steps,
                agent_name,
                tool=tool_name,
                status=status,
                detail=soft_fail or f"{tool_name} OK",
                data=_safe_preview(data) if isinstance(data, dict) else {},
            )
            summary_parts.append(f"{tool_name}: {'error' if soft_fail else 'ok'}")
            if isinstance(data, dict):
                _apply_tool_artifacts(artifacts, tool_name, data)
            if soft_fail:
                errors.append(soft_fail)
                break
        except Exception as exc:  # noqa: BLE001
            ok = False
            msg = str(exc)[:500]
            steps = _append_step(
                steps,
                agent_name,
                tool=tool_name,
                status="error",
                detail=msg,
            )
            summary_parts.append(f"{tool_name}: error")
            errors.append(msg)
            break

    if artifacts.get("article_id") and not article_id:
        article_id = int(artifacts["article_id"])

    # Crítica LLM del reviewer (asesora; no sustituye gates)
    if agent_name == "reviewer" and ok:
        try:
            reviews = artifacts.get("reviews") or []
            prompt = (
                "Eres revisor de marca de Autoridad 360 (voz Juan Vásquez: soberana, "
                "clara, sin hype). Resume en JSON: "
                '{"ok": true|false, "notes": "..."}.\n'
                f"Revisiones: {reviews[:8]}"
            )
            text, meta = fase5_ai.complete(db, task_type="agent_critique", prompt=prompt)
            critique = extract_json_object(text) or {"raw": (text or "")[:400]}
            artifacts["llm_critique"] = critique
            steps = _append_step(
                steps,
                agent_name,
                tool="llm_critique",
                status="ok",
                detail=str(critique.get("notes") or critique)[:400],
                data={"model": meta.get("model_used")},
            )
        except Exception as exc:  # noqa: BLE001
            steps = _append_step(
                steps,
                agent_name,
                tool="llm_critique",
                status="skip",
                detail=f"Crítica LLM omitida: {exc}",
            )

    package_id = artifacts.get("package_id") or state.get("package_id")
    summary = "; ".join(summary_parts) or "sin pasos"
    set_agent_status(
        agent_name,
        organization_id=org_id,
        status="completed" if ok else "failed",
        current_step=None,
        current_tool=None,
        run_id=state.get("run_id"),
        article_id=article_id,
        summary=summary[:400],
        ok=ok,
        error=None if ok else (errors[-1] if errors else summary)[:400],
    )
    return {
        "steps": steps,
        "artifacts": artifacts,
        "errors": errors,
        "ok": ok,
        "summary": summary,
        "article_id": article_id,
        "package_id": package_id,
    }


def make_agent_node(db: Session, agent_name: str) -> NodeFn:
    def node(state: EditorialState) -> dict[str, Any]:
        # Propagar org al session info para tools multi-tenant
        org_id = state.get("organization_id")
        if org_id is not None:
            db.info["organization_id"] = org_id
        started = time.perf_counter()
        updates = _run_agent_node(db, agent_name, state)
        updates.setdefault("summary", "")
        # Marca duración en el último step si hubo tools
        _ = started
        return updates

    node.__name__ = f"node_{agent_name}"
    return node


def bump_write_retry(state: EditorialState) -> dict[str, Any]:
    return {"retry_write": int(state.get("retry_write") or 0) + 1}


def route_after_review(state: EditorialState) -> str:
    critique = (state.get("artifacts") or {}).get("llm_critique") or {}
    retry = int(state.get("retry_write") or 0)
    max_r = int(state.get("max_write_retries") or 1)
    if isinstance(critique, dict) and critique.get("ok") is False and retry < max_r:
        return "retry"
    return "done"
