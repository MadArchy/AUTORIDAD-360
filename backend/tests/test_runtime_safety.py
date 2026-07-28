from __future__ import annotations

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError
from starlette.requests import Request

from app.config import Settings
from app.services.public_rate_limit import (
    enforce_public_lead_rate_limit,
    get_client_ip,
)


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key: str, seconds: int) -> bool:
        self.expirations[key] = seconds
        return True


class UnavailableRedis:
    def incr(self, _key: str) -> int:
        raise ConnectionError("unavailable")


def request_for(ip: str, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/public/leads",
            "headers": headers or [],
            "client": (ip, 1234),
        }
    )


def test_development_allows_local_defaults():
    Settings(app_env="development").assert_secure_production()


def test_pilot_rejects_default_secrets_and_seed_password():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY|DEV_SEED_PASSWORD"):
        Settings(app_env="pilot").assert_secure_production()


def test_pilot_accepts_distinct_generated_secrets():
    config = Settings(
        app_env="pilot",
        jwt_secret_key="j" * 32,
        api_key_encryption_key="a" * 32,
        session_secret_key="s" * 32,
        dev_seed_password="p" * 32,
    )
    config.assert_secure_production()


def test_rate_limit_rejects_requests_after_limit():
    config = Settings(public_lead_rate_limit=2, public_lead_rate_window_seconds=45)
    client = FakeRedis()
    request = request_for("203.0.113.18")

    enforce_public_lead_rate_limit(request, redis_client=client, config=config)
    enforce_public_lead_rate_limit(request, redis_client=client, config=config)
    with pytest.raises(HTTPException) as exc:
        enforce_public_lead_rate_limit(request, redis_client=client, config=config)

    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "45"}
    assert client.expirations["a360:rate-limit:public-leads:203.0.113.18"] == 45


def test_forwarded_for_is_used_only_for_trusted_proxy():
    headers = [(b"x-forwarded-for", b"198.51.100.10, 10.0.0.2")]
    request = request_for("10.0.0.2", headers)

    assert get_client_ip(request, Settings(trusted_proxy_ips="10.0.0.2")) == "198.51.100.10"
    assert get_client_ip(request, Settings()) == "10.0.0.2"


def test_rate_limit_fails_closed_when_redis_is_unavailable():
    with pytest.raises(HTTPException) as exc:
        enforce_public_lead_rate_limit(
            request_for("203.0.113.18"),
            redis_client=UnavailableRedis(),
            config=Settings(public_rate_limit_fail_open=False),
        )

    assert exc.value.status_code == 503
