"""T9: Upload cotización → stored, sha256 returned."""

import io
import pytest


@pytest.mark.asyncio
async def test_upload_cotizacion(auth_client):
    """T9: POST /cotizaciones/upload stores file, returns sha256."""
    # Create an RFQ and supplier first
    rfq_resp = await auth_client.post("/api/v2/rfqs", json={
        "title": "RFQ para cotización",
        "items": [{"description": "Cemento", "quantity": "100", "unit": "saco"}],
    })
    rfq_id = rfq_resp.json()["rfq"]["id"]

    supplier_resp = await auth_client.post("/api/v2/suppliers", json={
        "name": "Proveedor Test",
        "categories": ["construccion"],
    })
    supplier_id = supplier_resp.json()["supplier"]["id"]

    # Upload a fake PDF
    fake_pdf = b"%PDF-1.4 fake content for test"
    response = await auth_client.post(
        "/api/v2/cotizaciones/upload",
        data={"rfq_id": rfq_id, "supplier_id": supplier_id},
        files={"file": ("cotizacion.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert "sha256" in data
    assert "storage_ref" in data
    assert len(data["sha256"]) == 64  # SHA256 hex
