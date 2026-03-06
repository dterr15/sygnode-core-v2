"""T16: Case state machine — OPEN → FROZEN → ARCHIVED."""

import pytest


@pytest.mark.asyncio
async def test_case_transition_open_to_frozen(auth_client):
    """T16: Valid case transitions succeed."""
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento t16\n10 sacos cal t16",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    # Transition OPEN → FROZEN
    resp = await auth_client.post(f"/api/v2/cases/{case_id}/transition", json={
        "to_status": "FROZEN",
        "notes": "Caso congelado para auditoria",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "FROZEN"

    # Transition FROZEN → ARCHIVED
    resp2 = await auth_client.post(f"/api/v2/cases/{case_id}/transition", json={
        "to_status": "ARCHIVED",
    })
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_case_invalid_transition(auth_client):
    """T16b: FROZEN → OPEN (backwards) returns 409."""
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "100 kg fierro t16b",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    await auth_client.post(f"/api/v2/cases/{case_id}/transition", json={"to_status": "FROZEN"})

    # FROZEN → OPEN is invalid
    resp = await auth_client.post(f"/api/v2/cases/{case_id}/transition", json={
        "to_status": "OPEN",
    })
    assert resp.status_code == 409
