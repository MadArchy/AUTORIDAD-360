"""Auth refresh cookie + publish multi-canal (integración; requiere BD)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("APP_ENV", "development")
    try:
        from app.main import app
        from app.models import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"BD no disponible para tests de integración: {exc}")

    with TestClient(app) as c:
        yield c


def _login(client: TestClient):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "agencia@autoridad360.local", "password": "admin123"},
    )
    if r.status_code != 200:
        return None, None
    return {
        "Authorization": f"Bearer {r.json()['access_token']}",
        "X-Org-Slug": "agencia-piloto",
    }, r


def test_login_sets_httponly_refresh_cookie(client):
    headers, login_res = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    assert "a360_refresh" in login_res.cookies
    assert login_res.cookies.get("a360_refresh")
    assert login_res.json().get("expires_in_minutes", 0) <= 60


def test_refresh_rotates_access_token(client):
    headers, login_res = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    old = login_res.json()["access_token"]
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"] != old
    me = client.get(
        "/api/v1/orgs/me",
        headers={
            "Authorization": f"Bearer {refreshed.json()['access_token']}",
            "X-Org-Slug": "agencia-piloto",
        },
    )
    assert me.status_code == 200


def test_publish_requires_auth(client):
    assert client.get("/api/v1/publish/channels").status_code == 401
    assert client.get("/api/v1/publish/accounts").status_code == 401
    assert client.post("/api/v1/publish/packages", json={}).status_code == 401


def test_publish_assisted_package_flow(client):
    headers, _ = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")

    ch = client.get("/api/v1/publish/channels", headers=headers)
    assert ch.status_code == 200
    assert "linkedin" in ch.json()["channels"]

    accounts = client.get("/api/v1/publish/accounts", headers=headers)
    assert accounts.status_code == 200
    assert len(accounts.json()) >= 1

    posts = client.get("/api/v1/blog/published", headers=headers)
    assert posts.status_code == 200
    posts_data = posts.json()
    if not posts_data:
        pytest.skip("Sin blog posts publicados para construir paquete")

    source_id = posts_data[0]["id"]
    created = client.post(
        "/api/v1/publish/packages",
        headers=headers,
        json={
            "source_type": "blog_post",
            "source_id": source_id,
            "channels": ["linkedin", "facebook", "blog"],
        },
    )
    assert created.status_code == 200, created.text
    pkg = created.json()
    assert pkg["status"] == "ready"
    assert len(pkg["variants"]) == 3
    job_id = pkg["variants"][0]["job"]["id"]

    confirm = client.post(
        f"/api/v1/publish/jobs/{job_id}/confirm",
        headers=headers,
        json={"actor": "pytest", "external_url": "https://example.com/post/1"},
    )
    assert confirm.status_code == 200
    assert confirm.json()["job"]["status"] == "published"

    media = client.post(
        "/api/v1/publish/media",
        headers=headers,
        json={
            "title": "Cover pytest",
            "storage_url": "https://example.com/cover.jpg",
            "kind": "image",
            "aspect_ratio": "1:1",
        },
    )
    assert media.status_code == 200
    assert media.json()["title"] == "Cover pytest"
