"""
Basic smoke tests for the auth/session service.

Note: these require a real Supabase project (set via .env) since
auth_service calls the live Supabase Auth API — there's no local mock here.
For CI, point SUPABASE_URL/KEY at a dedicated test project, or mock
backend.db.supabase_client.get_anon_client / get_admin_client.
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_signup_requires_valid_email():
    response = client.post("/auth/signup", json={
        "email": "not-an-email",
        "password": "password123",
    })
    assert response.status_code == 422  # Pydantic EmailStr validation


def test_signup_requires_min_password_length():
    response = client.post("/auth/signup", json={
        "email": "test@example.com",
        "password": "short",
    })
    assert response.status_code == 422


def test_protected_route_without_token_returns_401():
    response = client.get("/chats")
    assert response.status_code in (401, 422)  # 422 if header missing entirely


def test_protected_route_with_garbage_token_returns_401():
    response = client.get("/chats", headers={"Authorization": "Bearer garbage_token"})
    assert response.status_code == 401
