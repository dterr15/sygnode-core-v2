"""T4: Intake paste → items parsed. T5: Deduplication."""

import pytest


@pytest.mark.asyncio
async def test_intake_paste(auth_client):
    """T4: Paste text → create list with parsed items."""
    response = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento\n10 sacos cal\n5 lt pintura blanca",
        "source": "whatsapp_paste",
    })
    assert response.status_code == 201
    data = response.json()
    assert "list_id" in data
    assert data["item_count"] == 3


@pytest.mark.asyncio
async def test_intake_paste_deduplication(auth_client):
    """T5: Same text → 409 DUPLICATE_PASTE."""
    text = "50 kg cemento dedup test\n10 sacos cal"

    resp1 = await auth_client.post("/api/v2/intake/paste", json={
        "text": text, "source": "whatsapp_paste",
    })
    assert resp1.status_code == 201

    resp2 = await auth_client.post("/api/v2/intake/paste", json={
        "text": text, "source": "whatsapp_paste",
    })
    assert resp2.status_code == 409
