"""Estado agregado de dependencias críticas, sin exponer secretos."""
from __future__ import annotations

import httpx
import redis
from sqlalchemy import text

from app.config import settings
from app.db.database import engine


def get_system_health() -> dict:
    dependencies: dict[str, dict] = {
        "database": {"ok": False},
        "redis": {"ok": False},
        "celery": {"ok": False},
        "ollama": {"ok": False},
    }
    dialect = engine.dialect.name
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        dependencies["database"] = {"ok": True, "dialect": dialect}
    except Exception as exc:  # noqa: BLE001
        dependencies["database"]["error"] = str(exc)[:160]

    try:
        client = redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
            protocol=2,
        )
        dependencies["redis"] = {"ok": bool(client.ping())}
    except Exception as exc:  # noqa: BLE001
        dependencies["redis"]["error"] = str(exc)[:160]

    try:
        from app.tasks import celery_app

        replies = celery_app.control.ping(timeout=0.75)
        dependencies["celery"] = {
            "ok": bool(replies),
            "workers": len(replies or []),
        }
    except Exception as exc:  # noqa: BLE001
        dependencies["celery"]["error"] = str(exc)[:160]

    try:
        response = httpx.get(
            f"{settings.ollama_base_url.rstrip('/')}/api/tags",
            timeout=1.5,
        )
        dependencies["ollama"] = {"ok": response.is_success}
    except Exception as exc:  # noqa: BLE001
        dependencies["ollama"]["error"] = str(exc)[:160]

    critical_ok = dependencies["database"]["ok"] and dependencies["redis"]["ok"]
    return {
        "status": "ok" if critical_ok else "degraded",
        "phase": "1-7",
        "app_env": settings.app_env,
        "db_dialect": dialect,
        "allow_header_auth": settings.allow_header_auth,
        "dependencies": dependencies,
    }
