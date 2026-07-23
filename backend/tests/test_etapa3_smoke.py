"""
Tests Etapa 3 (piloto) — corren contra la BD actual (Postgres offline OK).
MySQL real queda pendiente del pull Docker TLS.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    # Usa DATABASE_URL del entorno (Postgres piloto o SQLite smoke)
    os.environ.setdefault("APP_ENV", "development")
    from app.main import app

    with TestClient(app) as c:
        yield c


def _login_as(client, email: str, org_slug: str) -> dict | None:
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "admin123"},
    )
    if r.status_code != 200:
        return None
    return {
        "Authorization": f"Bearer {r.json()['access_token']}",
        "X-Org-Slug": org_slug,
    }


def _login(client) -> dict | None:
    return _login_as(client, "agencia@autoridad360.local", "agencia-piloto")


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "db_dialect" in data


def test_login_and_bearer(client):
    headers = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    me = client.get("/api/v1/orgs/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "agencia@autoridad360.local"


def test_ai_models_catalog(client):
    headers = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    r = client.get("/api/v1/ai/models", headers=headers)
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all("model_key" in m and "provider_type" in m for m in rows)


def test_blog_published_public(client):
    r = client.get("/api/v1/blog/published")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_blog_mutators_require_auth(client):
    assert client.get("/api/v1/blog/pending").status_code == 401
    assert client.post("/api/v1/blog/from-top10").status_code == 401
    assert (
        client.post(
            "/api/v1/blog/1/approve",
            json={"approved_by": "pytest"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/blog/1/reject",
            json={"approved_by": "pytest", "reason": "no"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/blog/1/publish",
            json={"approved_by": "pytest"},
        ).status_code
        == 401
    )


def test_blog_pending_with_auth(client):
    headers = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    r = client.get("/api/v1/blog/pending", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_cross_tenant_editorial_data_is_hidden(client):
    pilot = _login(client)
    north = _login_as(client, "norte@autoridad360.local", "agencia-norte")
    if not pilot or not north:
        pytest.skip("Seeds multiempresa no disponibles en esta BD")

    pilot_articles = client.get("/api/v1/articles?limit=5", headers=pilot)
    north_articles = client.get("/api/v1/articles?limit=5", headers=north)
    assert pilot_articles.status_code == 200
    assert north_articles.status_code == 200
    pilot_ids = {row["id"] for row in pilot_articles.json()}
    north_ids = {row["id"] for row in north_articles.json()}
    assert pilot_ids.isdisjoint(north_ids)
    if pilot_ids:
        hidden = client.get(
            f"/api/v1/articles/{next(iter(pilot_ids))}",
            headers=north,
        )
        assert hidden.status_code == 404

    pilot_jobs = client.get("/api/v1/jobs?limit=5", headers=pilot)
    north_jobs = client.get("/api/v1/jobs?limit=5", headers=north)
    assert pilot_jobs.status_code == 200
    assert north_jobs.status_code == 200
    pilot_job_ids = {row["id"] for row in pilot_jobs.json()}
    north_job_ids = {row["id"] for row in north_jobs.json()}
    assert pilot_job_ids.isdisjoint(north_job_ids)
    if pilot_job_ids:
        hidden = client.get(
            f"/api/v1/jobs/{next(iter(pilot_job_ids))}",
            headers=north,
        )
        assert hidden.status_code == 404

    isolated_collections = (
        ("/api/v1/content/packages?limit=5", "/api/v1/content/packages/{}"),
        ("/api/v1/ops/calendar?days=365", "/api/v1/ops/calendar/{}"),
        ("/api/v1/leads?limit=5", None),
        ("/api/v1/recommendations/percentages?limit=5", None),
        ("/api/v1/blog/pending", None),
    )
    for list_path, detail_path in isolated_collections:
        pilot_rows = client.get(list_path, headers=pilot)
        north_rows = client.get(list_path, headers=north)
        assert pilot_rows.status_code == 200, (list_path, pilot_rows.text)
        assert north_rows.status_code == 200, (list_path, north_rows.text)
        pilot_ids = {row["id"] for row in pilot_rows.json()}
        north_ids = {row["id"] for row in north_rows.json()}
        assert pilot_ids.isdisjoint(north_ids), list_path
        if detail_path and pilot_ids:
            hidden = client.get(
                detail_path.format(next(iter(pilot_ids))),
                headers=north,
            )
            assert hidden.status_code == 404


def test_content_and_jobs_require_auth(client):
    assert client.get("/api/v1/content/pending").status_code == 401
    assert client.get("/api/v1/jobs").status_code == 401
    assert client.post("/api/v1/jobs/collect?async_mode=true").status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        # Fase 1-3: lecturas internas y operaciones costosas/mutadoras.
        ("GET", "/api/v1/articles", None),
        ("GET", "/api/v1/articles/1", None),
        ("POST", "/api/v1/articles/1/classify", None),
        ("POST", "/api/v1/articles/1/verify", None),
        (
            "POST",
            "/api/v1/articles/1/reject",
            {"approved_by": "pytest", "reason": "Rechazo de prueba"},
        ),
        ("POST", "/api/v1/articles/1/analyze", None),
        ("GET", "/api/v1/top10", None),
        ("GET", "/api/v1/reports/latest", None),
        ("POST", "/api/v1/profile/seed", None),
        ("GET", "/api/v1/profile", None),
        ("GET", "/api/v1/profile/quota", None),
        (
            "PUT",
            "/api/v1/profile/percentages",
            {"editorial": [], "markets": []},
        ),
        ("POST", "/api/v1/content/from-article/1", None),
        ("GET", "/api/v1/content/packages", None),
        ("GET", "/api/v1/content/packages/1", None),
        # Proveedores y ejecución de IA.
        ("GET", "/api/v1/ai/providers", None),
        ("GET", "/api/v1/ai/models", None),
        (
            "POST",
            "/api/v1/ai/providers",
            {
                "name": "pytest",
                "provider_type": "ollama",
                "model_name": "test",
            },
        ),
        ("PATCH", "/api/v1/ai/providers/1", {"name": "pytest"}),
        ("DELETE", "/api/v1/ai/providers/1", None),
        ("POST", "/api/v1/ai/providers/1/test", None),
        ("GET", "/api/v1/ai/usage", None),
        ("GET", "/api/v1/ai/ollama/status", None),
        ("GET", "/api/v1/agents", None),
        ("GET", "/api/v1/agents/scout", None),
        ("POST", "/api/v1/agents/pipeline/run", {"mode": "discover"}),
        ("POST", "/api/v1/agents/scout/run", {}),
        # Operaciones editoriales.
        ("GET", "/api/v1/ops/news-typologies", None),
        ("POST", "/api/v1/ops/cadence/seed", None),
        ("GET", "/api/v1/ops/cadence", None),
        ("POST", "/api/v1/ops/search/run", None),
        ("POST", "/api/v1/ops/calendar/generate", {"weeks": 1}),
        ("GET", "/api/v1/ops/calendar", None),
        ("GET", "/api/v1/ops/calendar/1", None),
        (
            "POST",
            "/api/v1/ops/calendar/1/attach",
            {"actor": "pytest", "piece_id": 1},
        ),
        (
            "POST",
            "/api/v1/ops/calendar/1/advance",
            {"actor": "pytest", "target_status": "draft"},
        ),
        (
            "POST",
            "/api/v1/ops/calendar/1/prepare-approval",
            {"actor": "pytest"},
        ),
        ("GET", "/api/v1/ops/tasks", None),
        ("PATCH", "/api/v1/ops/tasks/1", {"actor": "pytest"}),
        ("GET", "/api/v1/ops/risk/piece/1", None),
        ("GET", "/api/v1/ops/decisions", None),
        # Métricas, leads y recomendaciones.
        ("GET", "/api/v1/metrics/dashboard", None),
        ("POST", "/api/v1/leads", {"contact_name": "Pytest User"}),
        ("GET", "/api/v1/leads", None),
        ("PATCH", "/api/v1/leads/1", {"status": "qualified"}),
        ("POST", "/api/v1/engagements", {}),
        ("POST", "/api/v1/recommendations/percentages/generate", None),
        ("GET", "/api/v1/recommendations/percentages", None),
        (
            "POST",
            "/api/v1/recommendations/percentages/1/decide",
            {"actor": "pytest", "accept": False},
        ),
    ],
)
def test_sensitive_endpoints_require_bearer_token(client, method, path, json_body):
    kwargs = {"json": json_body} if json_body is not None else {}
    response = client.request(method, path, **kwargs)
    assert response.status_code == 401, (method, path, response.text)


def test_production_rejects_header_auth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    # Re-import settings is tricky; validate property on fresh Settings
    from app.config import Settings

    s = Settings(app_env="production")
    assert s.is_production is True
    assert s.allow_header_auth is False


def test_job_idempotency_header_accepted(client):
    """Enqueue puede fallar sin Redis; al menos el endpoint no debe 500 por falta de header."""
    headers = _login(client)
    if not headers:
        pytest.skip("Usuario seed no disponible en esta BD")
    headers = {**headers, "Idempotency-Key": "pytest-collect-1"}
    r = client.post(
        "/api/v1/jobs/collect?async_mode=true",
        headers=headers,
    )
    # 200 queued/failed-with-fallback, o 503 si cola no disponible
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        body = r.json()
        assert body.get("job_name") == "collect"
        assert body.get("idempotency_key") == "pytest-collect-1"
        assert body.get("status") in {
            "queued",
            "running",
            "completed",
            "failed",
            "retrying",
        }
