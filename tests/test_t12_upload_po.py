"""T12: Upload PO → award inference → contrast."""

import io
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.schemas.enriched_contract import POExtraction


MOCK_PO = POExtraction(
    po_number="OC-2026-001",
    po_date="2026-03-01",
    po_issue_date_confidence="high",
    supplier_name="Proveedor Test SA",
    supplier_identification_confidence="high",
    total_amount=Decimal("150000"),
    currency="CLP",
    approved_by_name="Juan Pérez",
    approved_by_role="Gerente de Compras",
    items=[],
)


@pytest.mark.asyncio
async def test_upload_po(auth_client):
    """T12: Upload PO creates fulfillment + timeline events."""
    # Create intake → approve → get case_id
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "100 saco cemento t12\n50 kg cal t12",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    fake_pdf = b"%PDF-1.4 orden de compra test"

    with patch(
        "app.services.gemini_service.extract_po_data",
        new=AsyncMock(return_value=MOCK_PO),
    ), patch(
        "app.services.document_service.document_service.upload_document",
        new=AsyncMock(return_value=__import__("app.services.document_service", fromlist=["DocumentRef"]).DocumentRef(
            storage_ref="test/po/test.pdf",
            sha256_hash="a" * 64,
        )),
    ):
        resp = await auth_client.post(
            f"/api/v2/cases/{case_id}/upload-po",
            files={"file": ("oc.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "fulfillment_id" in data
    assert data["po_data"]["po_number"] == "OC-2026-001"
    assert "award" in data
    assert "contrast" in data
