"""T18: GET /auth/me — returns user + org for authenticated user."""

import pytest


@pytest.mark.asyncio
async def test_auth_me_authenticated(auth_client, test_user, test_org):
    """T18: GET /auth/me returns current user and organization."""
    response = await auth_client.get("/api/v2/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "organization" in data
    assert data["user"]["email"] == test_user.email
    assert data["user"]["role"] == test_user.role
    assert data["organization"]["rut"] == test_org.rut


@pytest.mark.asyncio
async def test_auth_me_unauthenticated(client):
    """T18b: GET /auth/me without cookie → 401."""
    response = await client.get("/api/v2/auth/me")
    assert response.status_code == 401
