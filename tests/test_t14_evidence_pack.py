"""T14: Evidence pack compilation — T15."""

import io
import pytest
from unittest.mock import AsyncMock, patch

from app.services.document_service import DocumentRef


@pytest.mark.asyncio
async def test_evidence_pack(auth_client):
    """T14/T15: GET /cases/:id/evidence-pack returns pack with integrity field."""
    # Create intake + approve → case
    paste_resp = await auth_client.post("/api/v2/intake/paste", json={
        "text": "50 kg cemento t14\n10 lt pintura t14",
        "source": "whatsapp_paste",
    })
    list_id = paste_resp.json()["list_id"]

    approve_resp = await auth_client.post(f"/api/v2/intake/{list_id}/approve", json={})
    case_id = approve_resp.json()["case_id"]

    # Get evidence pack
    resp = await auth_client.get(f"/api/v2/cases/{case_id}/evidence-pack")
    assert resp.status_code == 200
    data = resp.json()
    assert "evidence_pack" in data
    assert "integrity" in data
