import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import verify_password
from app.main import app
from app.models.user import User


@pytest.mark.anyio
async def test_register_success() -> None:
    payload = {
        "email": "User@Example.COM",
        "password": "very strong passphrase 123",
        "full_name": "Test User",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "user@example.com"
    assert "password_hash" not in data["user"]
    assert data["verification_required"] is False

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "user@example.com"))
        assert user is not None
        assert verify_password(payload["password"], user.password_hash) is True


@pytest.mark.anyio
async def test_register_duplicate_email_returns_409() -> None:
    payload = {"email": "dup@example.com", "password": "passphrase long enough"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/auth/register", json=payload)
        second = await client.post("/api/v1/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.anyio
async def test_register_rejects_short_password() -> None:
    payload = {"email": "a@example.com", "password": "short"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_invalid_email() -> None:
    payload = {"email": "not-an-email", "password": "passphrase long enough"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_register_concurrent_same_email() -> None:
    payload = {"email": "race@example.com", "password": "passphrase long enough"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        async def call():
            return await client.post("/api/v1/auth/register", json=payload)

        first, second = await asyncio.gather(call(), call())

    assert sorted([first.status_code, second.status_code]) == [201, 409]
