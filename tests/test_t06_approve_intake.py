"""T6: Approve intake → creates DecisionCase + CASE_CREATED event."""

import pytest


@pytest.mark.asyncio
async def test_approve_intake(auth_client):
    # Create intake first
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "100 kg fierro\n20 m cable", "source": "whatsapp_paste",
    })
    assert paste_resp.status_code == 201
    list_id = paste_resp.json()["list_id"]

    # Approve
    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={
        "notes": "Lista validada",
    })
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["success"] is True
    assert "case_id" in data

    # Verify intake status changed
    detail_resp = await auth_client.get(f"/api/v2/intake/{list_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["list"]["validation_status"] == "APPROVED_GENERATED"
    assert detail["list"]["validated_by_user_id"] is not None
