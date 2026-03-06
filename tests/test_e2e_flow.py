"""E2E: Full procurement flow a→k."""

import io
import json
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.schemas.enriched_contract import (
    QuoteExtraction, QuoteExtractionItem, AnalysisData,
    AnalysisDistribution, POExtraction,
)

MOCK_EXTRACTION = QuoteExtraction(
    supplier_name="Proveedor E2E SA",
    currency="CLP",
    total_amount=Decimal("150000"),
    freight_total=Decimal("0"),
    items=[QuoteExtractionItem(
        description="Cemento portland 42.5kg",
        quantity=Decimal("100"),
        unit="saco",
        unit_price=Decimal("1500"),
        subtotal=Decimal("150000"),
        match_confidence=0.92,
    )],
)

MOCK_ANALYSIS = AnalysisData(
    recommendation="Adjudicar a Proveedor E2E SA por mejor precio",
    strategy="BTC",
    distribution=[AnalysisDistribution(
        supplier_name="Proveedor E2E SA",
        items_awarded=["Cemento portland"],
        amount_awarded=Decimal("150000"),
    )],
)

MOCK_PO = POExtraction(
    po_number="OC-E2E-001",
    total_amount=Decimal("150000"),
    currency="CLP",
    po_issue_date_confidence="high",
    supplier_identification_confidence="high",
)


@pytest.mark.asyncio
async def test_full_e2e_flow(auth_client):
    """E2E: steps a → k of full procurement flow."""

    # a) POST /intake/paste
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "100 sacos cemento portland 42.5kg\n5 tambores aceite hidráulico",
        "source": "whatsapp_paste",
    })
    assert paste_resp.status_code == 201, paste_resp.text
    list_id = paste_resp.json()["list_id"]
    assert paste_resp.json()["item_count"] == 2

    # b) POST /intake/:id/approve
    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    assert approve_resp.status_code == 200, approve_resp.text
    case_id = approve_resp.json()["case_id"]

    # c) POST /intake/:id/transition { to_status: "EN_COTIZACION" }
    trans_resp = await auth_client.post(f"/api/v2/intake/{list_id}/transition", json={
        "to_status": "EN_COTIZACION",
    })
    assert trans_resp.status_code == 200, trans_resp.text
    assert trans_resp.json()["status"] == "EN_COTIZACION"

    # d) POST /rfqs
    rfq_resp = await auth_client.post("/api/v2/rfqs", json={
        "title": "RFQ Cemento E2E",
        "items": [
            {"description": "Cemento portland 42.5kg", "quantity": "100", "unit": "saco"},
        ],
    })
    assert rfq_resp.status_code == 201, rfq_resp.text
    rfq_id = rfq_resp.json()["rfq"]["id"]

    # e) POST /cotizaciones/upload
    fake_pdf = b"%PDF-1.4 fake cotizacion e2e"
    with patch(
        "app.services.document_service.document_service.upload_document",
        new=AsyncMock(return_value=__import__(
            "app.services.document_service", fromlist=["DocumentRef"]
        ).DocumentRef(storage_ref="e2e/cot/test.pdf", sha256_hash="a" * 64)),
    ):
        supplier_resp = await auth_client.post("/api/v2/suppliers", json={
            "name": "Proveedor E2E SA",
            "categories": ["construccion"],
        })
        supplier_id = supplier_resp.json()["supplier"]["id"]

        upload_resp = await auth_client.post(
            "/api/v2/cotizaciones/upload",
            data={"rfq_id": rfq_id, "supplier_id": supplier_id},
            files={"file": ("cotizacion.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        )
    assert upload_resp.status_code == 201, upload_resp.text
    document_id = upload_resp.json()["document_id"]

    # f) POST /cotizaciones/:id/process
    with patch(
        "app.services.gemini_service.extract_quote_from_document",
        new=AsyncMock(return_value=MOCK_EXTRACTION),
    ), patch(
        "app.services.document_service.document_service.get_document_bytes",
        new=AsyncMock(return_value=fake_pdf),
    ):
        process_resp = await auth_client.post(
            f"/api/v2/cotizaciones/{document_id}/process",
            json={"rfq_items": [{"description": "Cemento portland", "unit": "saco"}]},
        )
    assert process_resp.status_code == 200, process_resp.text
    assert process_resp.json()["extracted"]["supplier_name"] == "Proveedor E2E SA"

    # g) POST /rfqs/:id/analyze
    with patch(
        "app.services.gemini_service.generate_comparative_analysis",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        analyze_resp = await auth_client.post(f"/api/v2/rfqs/{rfq_id}/analyze", json={
            "items_summary": {"cemento": {"Proveedor E2E SA": 150000}},
            "context": "Proyecto construccion",
        })
    assert analyze_resp.status_code == 200, analyze_resp.text
    assert analyze_resp.json()["analysis"]["strategy"] == "BTC"

    # h) The case was created at step b. Verify it's OPEN.
    case_resp = await auth_client.get(f"/api/v2/cases/{case_id}")
    assert case_resp.status_code == 200, case_resp.text
    assert case_resp.json()["case"]["status"] == "OPEN"

    # i) POST /cases/:id/upload-po
    fake_po = b"%PDF-1.4 fake po e2e"
    with patch(
        "app.services.gemini_service.extract_po_data",
        new=AsyncMock(return_value=MOCK_PO),
    ), patch(
        "app.services.document_service.document_service.upload_document",
        new=AsyncMock(return_value=__import__(
            "app.services.document_service", fromlist=["DocumentRef"]
        ).DocumentRef(storage_ref="e2e/po/test.pdf", sha256_hash="b" * 64)),
    ):
        po_resp = await auth_client.post(
            f"/api/v2/cases/{case_id}/upload-po",
            files={"file": ("oc.pdf", io.BytesIO(fake_po), "application/pdf")},
        )
    assert po_resp.status_code == 200, po_resp.text
    assert po_resp.json()["po_data"]["po_number"] == "OC-E2E-001"

    # j) GET /cases/:id/verify-chain
    chain_resp = await auth_client.get(f"/api/v2/cases/{case_id}/verify-chain")
    assert chain_resp.status_code == 200, chain_resp.text
    assert chain_resp.json()["intact"] is True

    # k) GET /cases/:id/evidence-pack
    pack_resp = await auth_client.get(f"/api/v2/cases/{case_id}/evidence-pack")
    assert pack_resp.status_code == 200, pack_resp.text
    pack = pack_resp.json()
    assert pack["integrity"]["intact"] is True
    assert "pack_signature" in pack["evidence_pack"]
