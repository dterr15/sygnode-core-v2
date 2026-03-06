"""T20: Justify variance — no extra timeline event generated."""

import io
import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.schemas.enriched_contract import POExtraction


def _mock_po(amount: Decimal) -> POExtraction:
    return POExtraction(
        po_number="OC-2026-002",
        total_amount=amount,
        currency="CLP",
        po_issue_date_confidence="high",
        supplier_identification_confidence="high",
    )


@pytest.mark.asyncio
async def test_justify_variance_no_fulfillment(auth_client):
    """T20: Justify on case without fulfillment → 404."""
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "100 kg fierro t20",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]
    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    resp = await auth_client.post(f"/api/v2/cases/{case_id}/justify-variance", json={
        "justification": "Precio ajustado por inflación",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_justify_variance_not_required(auth_client):
    """T20b: Justify on case that doesn't require justification → 409."""
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento t20b\n10 lt pintura t20b",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]
    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    fake_pdf = b"%PDF-1.4 oc test t20b"
    with patch(
        "app.services.gemini_service.extract_po_data",
        new=AsyncMock(return_value=_mock_po(Decimal("50000"))),
    ), patch(
        "app.services.document_service.document_service.upload_document",
        new=AsyncMock(return_value=__import__(
            "app.services.document_service", fromlist=["DocumentRef"]
        ).DocumentRef(storage_ref="test/po/t20b.pdf", sha256_hash="b" * 64)),
    ):
        await auth_client.post(
            f"/api/v2/cases/{case_id}/upload-po",
            files={"file": ("oc.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        )

    # requires_justification is False by default (delta=0)
    resp = await auth_client.post(f"/api/v2/cases/{case_id}/justify-variance", json={
        "justification": "No es necesaria justificación",
    })
    assert resp.status_code == 409
