"""Tests for auth API: register, login, refresh, logout, me."""

import uuid

import pytest
from httpx import AsyncClient

from conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD, TEST_USER_FULL_NAME


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Register returns 201 and user without password; sets cookies."""
    email = _unique_email()
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "full_name": "New User",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == email
    assert data["full_name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data
    # Cookie name may be set by backend (e.g. access_token)
    assert len(r.cookies) >= 1


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Register with existing email returns 409."""
    email = _unique_email()
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "full_name": "Dup",
        },
    )
    assert r.status_code == 201
    r2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "other",
            "full_name": "Dup2",
        },
    )
    assert r2.status_code == 409
    assert "already" in r2.json().get("detail", "").lower() or "registered" in r2.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session):
    """Login with valid credentials returns 200 and sets cookies."""
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    email = _unique_email()
    user = User(
        email=email,
        hashed_password=get_password_hash("mypass"),
        full_name="Login User",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "mypass"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == email
    assert len(r.cookies) >= 1


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session):
    """Login with wrong password returns 401."""
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    email = _unique_email()
    user = User(
        email=email,
        hashed_password=get_password_hash("right"),
        full_name="No Pass",
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()

    r = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    """GET /auth/me without token returns 401."""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_cookies(auth_client: AsyncClient):
    """GET /auth/me with session cookies returns current user."""
    r = await auth_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert "email" in data
    assert data["full_name"] == TEST_USER_FULL_NAME


@pytest.mark.asyncio
async def test_me_with_bearer(client: AsyncClient, auth_headers: dict):
    """GET /auth/me with Bearer token returns current user."""
    email = auth_headers.get("_email")
    headers = {k: v for k, v in auth_headers.items() if not k.startswith("_")}
    r = await client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == email


@pytest.mark.asyncio
async def test_refresh_with_cookie(auth_client: AsyncClient):
    """POST /auth/refresh with refresh cookie returns 200 and new cookies."""
    r = await auth_client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert r.json().get("message") == "Tokens refreshed"


@pytest.mark.asyncio
async def test_refresh_without_cookie(client: AsyncClient):
    """POST /auth/refresh without cookie returns 401."""
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout(auth_client: AsyncClient):
    """POST /auth/logout clears cookies; then /auth/me returns 401."""
    r = await auth_client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    r2 = await auth_client.get("/api/v1/auth/me")
    assert r2.status_code == 401
