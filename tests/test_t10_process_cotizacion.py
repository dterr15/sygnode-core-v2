"""T10: Process cotización with Gemini mock — validates JSON contract."""

import io
import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.enriched_contract import QuoteExtraction, QuoteExtractionItem
from decimal import Decimal


MOCK_EXTRACTION = QuoteExtraction(
    supplier_name="Proveedor Mock SA",
    currency="CLP",
    total_amount=Decimal("150000"),
    freight_total=Decimal("0"),
    items=[
        QuoteExtractionItem(
            description="Cemento portland 42.5kg",
            quantity=Decimal("100"),
            unit="saco",
            unit_price=Decimal("1500"),
            subtotal=Decimal("150000"),
            match_confidence=0.92,
        )
    ],
)


@pytest.mark.asyncio
async def test_process_cotizacion_gemini(auth_client):
    """T10: Processing with mocked Gemini extracts data + validates contract."""
    # Create RFQ + supplier + upload file
    rfq_resp = await auth_client.post("/api/v2/rfqs", json={
        "title": "RFQ proceso cotización",
        "items": [{"description": "Cemento portland", "quantity": "100", "unit": "saco"}],
    })
    rfq_id = rfq_resp.json()["rfq"]["id"]

    supplier_resp = await auth_client.post("/api/v2/suppliers", json={
        "name": "Proveedor Proceso",
        "categories": ["construccion"],
    })
    supplier_id = supplier_resp.json()["supplier"]["id"]

    # Upload fake PDF
    fake_pdf = b"%PDF-1.4 fake cotizacion"
    upload_resp = await auth_client.post(
        "/api/v2/cotizaciones/upload",
        data={"rfq_id": rfq_id, "supplier_id": supplier_id},
        files={"file": ("cotizacion.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert upload_resp.status_code == 201
    document_id = upload_resp.json()["document_id"]

    # Process with mocked Gemini (G6: explicit trigger)
    with patch(
        "app.services.gemini_service.extract_quote_from_document",
        new=AsyncMock(return_value=MOCK_EXTRACTION),
    ):
        process_resp = await auth_client.post(
            f"/api/v2/cotizaciones/{document_id}/process",
            json={"rfq_items": [{"description": "Cemento portland", "unit": "saco"}]},
        )

    assert process_resp.status_code == 200
    data = process_resp.json()
    assert "extracted" in data
    assert data["extracted"]["supplier_name"] == "Proveedor Mock SA"
    assert data["extracted"]["currency"] == "CLP"
    assert len(data["items_matched"]) == 1
