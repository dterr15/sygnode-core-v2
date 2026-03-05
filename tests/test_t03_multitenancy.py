"""T3: Multi-tenant isolation — user only sees own org's data."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User
from app.models.rfq import RFQ
from app.services.auth_service import hash_password


@pytest.mark.asyncio
async def test_multitenancy_isolation(auth_client, db: AsyncSession, test_org, test_user):
    # Create RFQ for test_org
    rfq_a = RFQ(
        organization_id=test_org.id,
        reference_code="RFQ-2026-0001",
        title="RFQ Org A",
        created_by=test_user.id,
    )
    db.add(rfq_a)

    # Create another org with its own RFQ
    org_b = Organization(rut="98.765.432-1", name="Other Org")
    db.add(org_b)
    await db.flush()

    rfq_b = RFQ(
        organization_id=org_b.id,
        reference_code="RFQ-2026-0001",
        title="RFQ Org B",
    )
    db.add(rfq_b)
    await db.commit()

    # User from org_a should only see org_a's RFQs
    response = await auth_client.get("/api/v2/rfqs")
    assert response.status_code == 200
    data = response.json()
    titles = [r["title"] for r in data["items"]]
    assert "RFQ Org A" in titles
    assert "RFQ Org B" not in titles
