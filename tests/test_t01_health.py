"""T1: Health check — GET /api/v2/health → 200."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v2/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "2.0"
