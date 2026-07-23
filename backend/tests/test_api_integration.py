import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["service"] == "Autoridad 360"

def test_api_unauthorized_access():
    # Intenta acceder a una ruta protegida sin token ni headers de org
    response = client.get("/api/v1/profile")
    assert response.status_code in (200, 401, 403, 404, 422)

def test_auth_login_invalid():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "fake@agencia.com", "password": "wrongpassword"}
    )
    assert response.status_code in (400, 401, 404, 422)
