"""T11: Comparative analysis — validates JSON contract schema."""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from app.schemas.enriched_contract import AnalysisData, AnalysisDistribution


MOCK_ANALYSIS = AnalysisData(
    recommendation="Adjudicar a Proveedor A por mejor precio y plazo",
    strategy="BTC",
    distribution=[
        AnalysisDistribution(
            supplier_name="Proveedor A",
            items_awarded=["Cemento portland"],
            amount_awarded=Decimal("150000"),
            rationale="Menor precio unitario",
        )
    ],
    item_analysis=[],
)


@pytest.mark.asyncio
async def test_analyze_rfq(auth_client):
    """T11: POST /rfqs/:id/analyze with mocked Gemini returns analysis."""
    rfq_resp = await auth_client.post("/api/v2/rfqs", json={
        "title": "RFQ análisis comparativo",
        "items": [{"description": "Cemento portland", "quantity": "100", "unit": "saco"}],
    })
    rfq_id = rfq_resp.json()["rfq"]["id"]

    with patch(
        "app.services.gemini_service.generate_comparative_analysis",
        new=AsyncMock(return_value=MOCK_ANALYSIS),
    ):
        resp = await auth_client.post(f"/api/v2/rfqs/{rfq_id}/analyze", json={
            "items_summary": {"cemento": {"count": 1, "best_price": 1500}},
            "context": "Proyecto construcción 2026",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "analysis" in data
    analysis = data["analysis"]
    assert analysis["strategy"] == "BTC"
    assert "recommendation" in analysis
    assert len(analysis["distribution"]) >= 1
