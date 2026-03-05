"""T7: Invalid state transition returns 409."""

import pytest


@pytest.mark.asyncio
async def test_invalid_intake_transition(auth_client):
    # Create and approve intake first
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento t7", "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    # Approve it
    await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})

    # Try invalid transition: PENDIENTE_REVISION → CERRADA (not allowed)
    resp = await auth_client.post(f"/api/v2/intake/{list_id}/transition", json={
        "to_status": "CERRADA",
    })
    assert resp.status_code == 409
    assert "no permitida" in resp.json()["detail"]
