"""T8: Create RFQ with items → reference_code generated."""

import pytest


@pytest.mark.asyncio
async def test_create_rfq(auth_client):
    """T8: POST /rfqs creates RFQ with items and returns reference_code."""
    response = await auth_client.post("/api/v2/rfqs", json={
        "title": "Compra materiales construcción",
        "description": "Cemento, cal y pintura",
        "items": [
            {"description": "Cemento portland", "quantity": "50", "unit": "saco"},
            {"description": "Cal viva", "quantity": "10", "unit": "kg"},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert "rfq" in data
    rfq = data["rfq"]
    assert "id" in rfq
    assert "reference_code" in rfq
    assert rfq["reference_code"].startswith("RFQ-")
    assert rfq["status"] == "draft"


@pytest.mark.asyncio
async def test_list_rfqs(auth_client):
    """GET /rfqs returns paginated list from user's org."""
    await auth_client.post("/api/v2/rfqs", json={
        "title": "RFQ Test List",
        "items": [{"description": "Item A", "quantity": "1", "unit": "un"}],
    })
    response = await auth_client.get("/api/v2/rfqs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1
