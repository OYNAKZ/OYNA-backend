from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"

VALID_USER = {
    "full_name": "Test User",
    "email": "test@example.com",
    "phone": "+77001234567",
    "password": "strongpass123",
}


def test_register_success() -> None:
    response = client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == VALID_USER["email"]
    assert body["full_name"] == VALID_USER["full_name"]
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email() -> None:
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(REGISTER_URL, json=VALID_USER)
    assert response.status_code == 409


def test_register_duplicate_phone() -> None:
    client.post(REGISTER_URL, json=VALID_USER)
    different_email = {**VALID_USER, "email": "other@example.com"}
    response = client.post(REGISTER_URL, json=different_email)
    assert response.status_code == 409


def test_login_success() -> None:
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": VALID_USER["password"]})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_wrong_password() -> None:
    client.post(REGISTER_URL, json=VALID_USER)
    response = client.post(LOGIN_URL, json={"email": VALID_USER["email"], "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_unknown_email() -> None:
    response = client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "irrelevant"})
    assert response.status_code == 401
