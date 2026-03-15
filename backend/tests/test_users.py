"""Tests for users API: GET /users/me, PATCH /users/me."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient):
    """GET /users/me without auth returns 401."""
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(auth_client: AsyncClient):
    """GET /users/me returns current user profile."""
    r = await auth_client.get("/api/v1/users/me")
    assert r.status_code == 200
    data = r.json()
    assert "email" in data
    assert "full_name" in data
    assert "id" in data
    assert "role" in data


@pytest.mark.asyncio
async def test_update_me_full_name(auth_client: AsyncClient):
    """PATCH /users/me updates full_name."""
    r = await auth_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Updated Name"},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Updated Name"
    r2 = await auth_client.get("/api/v1/users/me")
    assert r2.json()["full_name"] == "Updated Name"
