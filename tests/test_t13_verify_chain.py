"""T13: Verify chain integrity returns intact=true."""

import pytest


@pytest.mark.asyncio
async def test_verify_chain_integrity(auth_client):
    # Create intake + approve (creates case + CASE_CREATED event)
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento t13\n10 sacos cal t13", "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    # Verify chain
    chain_resp = await auth_client.get(f"/api/v2/cases/{case_id}/verify-chain")
    assert chain_resp.status_code == 200
    data = chain_resp.json()
    assert data["intact"] is True
    assert data["total_events"] >= 1
    assert data["broken_at"] is None
