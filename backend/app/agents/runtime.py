"""Estado en vivo y prioridad de agentes editoriales (Redis + fallback memoria)."""

from __future__ import annotations

import json
import threading
import time
from typing import Any

from app.agents.roles import AGENTS

# Prioridad operativa del ciclo automático (1 = más urgente).
AGENT_PRIORITY: list[dict[str, Any]] = [
    {
        "name": "scout",
        "priority": 1,
        "auto": True,
        "phase": "discover",
        "function": "Buscar tipologías del día (regulación, fallos, PI, MX–US)",
    },
    {
        "name": "classifier",
        "priority": 2,
        "auto": True,
        "phase": "ingest",
        "function": "Clasificar lote de noticias recolectadas",
    },
    {
        "name": "verifier",
        "priority": 3,
        "auto": True,
        "phase": "quality",
        "function": "Verificar grounding y publicabilidad",
    },
    {
        "name": "writer",
        "priority": 4,
        "auto": True,
        "phase": "produce",
        "function": "Generar paquete multi-formato de piezas verificadas",
    },
    {
        "name": "reviewer",
        "priority": 5,
        "auto": True,
        "phase": "quality",
        "function": "Gates factual + marca antes de aprobar",
    },
    {
        "name": "trend_ad_advisor",
        "priority": 6,
        "auto": True,
        "phase": "trends",
        "function": "Notas de tendencia y CTAs orgánicos por red",
    },
    {
        "name": "juan_editorial",
        "priority": 7,
        "auto": True,
        "phase": "juan",
        "function": "Paquete editorial con voz Juan",
    },
    {
        "name": "juan_ai_governance",
        "priority": 8,
        "auto": True,
        "phase": "juan",
        "function": "Brief AI Readiness (Education / Technology / Governance)",
    },
    {
        "name": "juan_ip_patents",
        "priority": 9,
        "auto": True,
        "phase": "juan",
        "function": "Brief PI/patentes (prosecution, FTO, inventorship)",
    },
]

_PRIORITY_BY_NAME = {a["name"]: a for a in AGENT_PRIORITY}
_MEM_LOCK = threading.Lock()
_MEM_STATUS: dict[str, dict[str, Any]] = {}
_MEM_CYCLE: dict[str, dict[str, Any]] = {}


def _org_key(organization_id: int | None) -> str:
    return str(organization_id if organization_id is not None else 0)


def _redis():
    try:
        import redis as redis_mod
        from app.config import settings

        kwargs: dict[str, Any] = {
            "decode_responses": True,
            "socket_connect_timeout": 1.5,
            "socket_timeout": 1.5,
        }
        if int(getattr(redis_mod, "__version__", "0").split(".")[0] or 0) >= 5:
            kwargs["protocol"] = 2
        client = redis_mod.from_url(settings.redis_url, **kwargs)
        client.ping()
        return client
    except Exception:
        return None


def _default_row(meta: dict[str, Any]) -> dict[str, Any]:
    agent = AGENTS.get(meta["name"])
    return {
        "name": meta["name"],
        "priority": meta["priority"],
        "auto": meta["auto"],
        "phase": meta["phase"],
        "function": meta["function"],
        "role": agent.role if agent else "",
        "tools": list(agent.tools) if agent else [],
        "task_type": agent.task_type if agent else "",
        "status": "idle",
        "current_step": None,
        "current_tool": None,
        "run_id": None,
        "article_id": None,
        "summary": None,
        "ok": None,
        "started_at": None,
        "finished_at": None,
        "updated_at": None,
        "error": None,
    }


def _status_key(organization_id: int | None) -> str:
    return f"a360:agent_status:{_org_key(organization_id)}"


def _cycle_key(organization_id: int | None) -> str:
    return f"a360:agent_cycle:{_org_key(organization_id)}"


def _lock_key(organization_id: int | None) -> str:
    return f"a360:agent_cycle_lock:{_org_key(organization_id)}"


def get_agent_board(organization_id: int | None = None) -> dict[str, Any]:
    """Tablero completo: prioridad, estado y función de cada agente."""
    stored: dict[str, dict[str, Any]] = {}
    client = _redis()
    if client is not None:
        try:
            raw = client.hgetall(_status_key(organization_id)) or {}
            for name, payload in raw.items():
                try:
                    stored[name] = json.loads(payload)
                except Exception:
                    continue
        except Exception:
            stored = {}
    else:
        with _MEM_LOCK:
            stored = dict(_MEM_STATUS.get(_org_key(organization_id), {}))

    agents = []
    for meta in AGENT_PRIORITY:
        row = _default_row(meta)
        if meta["name"] in stored:
            row.update({k: v for k, v in stored[meta["name"]].items() if v is not None})
            # Campos canónicos no pisados por basura
            row["priority"] = meta["priority"]
            row["auto"] = meta["auto"]
            row["phase"] = meta["phase"]
            row["function"] = meta["function"]
        agents.append(row)

    cycle = get_cycle_state(organization_id)
    active = [a for a in agents if a.get("status") in {"running", "queued"}]
    return {
        "agents": agents,
        "active_count": len(active),
        "active": [a["name"] for a in active],
        "cycle": cycle,
        "priority_order": [a["name"] for a in AGENT_PRIORITY],
    }


def set_agent_status(
    name: str,
    *,
    organization_id: int | None = None,
    status: str,
    current_step: str | None = None,
    current_tool: str | None = None,
    run_id: str | None = None,
    article_id: int | None = None,
    summary: str | None = None,
    ok: bool | None = None,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    meta = _PRIORITY_BY_NAME.get(name) or {
        "name": name,
        "priority": 99,
        "auto": False,
        "phase": "manual",
        "function": "Ejecución manual",
    }
    row = _default_row(meta)
    # merge previous
    board = get_agent_board(organization_id)
    prev = next((a for a in board["agents"] if a["name"] == name), None)
    if prev:
        row.update(prev)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    row.update(
        {
            "status": status,
            "current_step": current_step,
            "current_tool": current_tool,
            "run_id": run_id if run_id is not None else row.get("run_id"),
            "article_id": article_id if article_id is not None else row.get("article_id"),
            "summary": summary if summary is not None else row.get("summary"),
            "ok": ok if ok is not None else row.get("ok"),
            "error": error,
            "updated_at": now,
        }
    )
    if started_at is not None:
        row["started_at"] = started_at
    elif status == "running" and not row.get("started_at"):
        row["started_at"] = now
    if finished_at is not None:
        row["finished_at"] = finished_at
    elif status in {"idle", "completed", "failed"}:
        row["finished_at"] = now
        if status == "idle" and ok is None and error is None:
            # idle limpio post-ciclo
            pass

    client = _redis()
    if client is not None:
        try:
            client.hset(_status_key(organization_id), name, json.dumps(row, ensure_ascii=False))
            client.expire(_status_key(organization_id), 60 * 60 * 48)
        except Exception:
            pass
    else:
        with _MEM_LOCK:
            bucket = _MEM_STATUS.setdefault(_org_key(organization_id), {})
            bucket[name] = row
    return row


def set_cycle_state(
    organization_id: int | None,
    *,
    status: str,
    phase: str | None = None,
    current_agent: str | None = None,
    summary: str | None = None,
    ok: bool | None = None,
    job_id: int | None = None,
    steps_done: list[str] | None = None,
) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prev = get_cycle_state(organization_id)
    payload = {
        **prev,
        "status": status,
        "phase": phase if phase is not None else prev.get("phase"),
        "current_agent": current_agent,
        "summary": summary if summary is not None else prev.get("summary"),
        "ok": ok if ok is not None else prev.get("ok"),
        "job_id": job_id if job_id is not None else prev.get("job_id"),
        "steps_done": steps_done if steps_done is not None else prev.get("steps_done") or [],
        "updated_at": now,
    }
    if status == "running" and not prev.get("started_at"):
        payload["started_at"] = now
    if status in {"completed", "failed", "idle"}:
        payload["finished_at"] = now

    client = _redis()
    if client is not None:
        try:
            client.set(
                _cycle_key(organization_id),
                json.dumps(payload, ensure_ascii=False),
                ex=60 * 60 * 48,
            )
        except Exception:
            pass
    else:
        with _MEM_LOCK:
            _MEM_CYCLE[_org_key(organization_id)] = payload
    return payload


def get_cycle_state(organization_id: int | None = None) -> dict[str, Any]:
    default = {
        "status": "idle",
        "phase": None,
        "current_agent": None,
        "summary": None,
        "ok": None,
        "job_id": None,
        "steps_done": [],
        "started_at": None,
        "finished_at": None,
        "updated_at": None,
    }
    client = _redis()
    if client is not None:
        try:
            raw = client.get(_cycle_key(organization_id))
            if raw:
                data = json.loads(raw)
                return {**default, **data}
        except Exception:
            pass
    with _MEM_LOCK:
        return {**default, **(_MEM_CYCLE.get(_org_key(organization_id)) or {})}


def try_acquire_cycle_lock(organization_id: int | None, ttl_sec: int = 45 * 60) -> bool:
    client = _redis()
    token = f"{time.time()}"
    if client is not None:
        try:
            return bool(client.set(_lock_key(organization_id), token, nx=True, ex=ttl_sec))
        except Exception:
            pass
    with _MEM_LOCK:
        key = _org_key(organization_id)
        cur = _MEM_CYCLE.get(f"lock:{key}")
        now = time.time()
        if cur and now - float(cur) < ttl_sec:
            return False
        _MEM_CYCLE[f"lock:{key}"] = str(now)
        return True


def release_cycle_lock(organization_id: int | None) -> None:
    client = _redis()
    if client is not None:
        try:
            client.delete(_lock_key(organization_id))
        except Exception:
            pass
    with _MEM_LOCK:
        _MEM_CYCLE.pop(f"lock:{_org_key(organization_id)}", None)


def describe_priority_catalog() -> list[dict[str, Any]]:
    return [dict(a) for a in AGENT_PRIORITY]
