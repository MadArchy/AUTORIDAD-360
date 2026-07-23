"""E2E mínimo (API): health → login → branding público → attribution."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Solo corre si hay DB real configurada (piloto); se salta en CI sqlite puro sin seed.
RUN = os.environ.get("A360_E2E", "").strip() in {"1", "true", "yes"}


@pytest.mark.skipif(not RUN, reason="Set A360_E2E=1 with live Postgres piloto")
def test_e2e_login_branding_health():
    from app.main import app

    client = TestClient(app)
    h = client.get("/api/v1/health")
    assert h.status_code == 200
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code in (200, 503)

    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@autoridad360.local",
            "password": "admin123",
            "organization_slug": "juan-vasquez",
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    brand = client.get("/api/v1/public/branding", params={"host": "127.0.0.1"})
    assert brand.status_code == 200
    assert brand.json().get("display_name")

    attr = client.get("/api/v1/marketing/attribution?days=30", headers=auth)
    assert attr.status_code == 200
