"""Redis-backed rate limiting for unauthenticated endpoints."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError

from app.config import Settings, settings

logger = logging.getLogger(__name__)


def get_client_ip(request: Request, config: Settings = settings) -> str:
    """Use forwarded IPs only from an explicitly trusted proxy."""
    direct_ip = request.client.host if request.client else "unknown"
    if direct_ip in config.trusted_proxy_ip_set():
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or direct_ip
    return direct_ip


def enforce_public_lead_rate_limit(
    request: Request,
    *,
    redis_client: Redis | None = None,
    config: Settings = settings,
) -> None:
    """Raise 429 when an IP exceeds the configured public lead submission rate."""
    limit = max(1, config.public_lead_rate_limit)
    window_seconds = max(1, config.public_lead_rate_window_seconds)
    client = redis_client or Redis.from_url(config.redis_url, decode_responses=True)
    key = f"a360:rate-limit:public-leads:{get_client_ip(request, config)}"

    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, window_seconds)
    except RedisError as exc:
        logger.warning("public_lead_rate_limit_unavailable error=%r", exc)
        if config.public_rate_limit_fail_open:
            return
        raise HTTPException(
            status_code=503,
            detail="La captura de leads no está disponible temporalmente.",
        ) from exc

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail="Demasiadas solicitudes. Intenta de nuevo más tarde.",
            headers={"Retry-After": str(window_seconds)},
        )
