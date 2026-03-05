"""RFQ service — create, update, transition."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.state_machines import validate_rfq_transition
from app.models.rfq import RFQ, RFQItem
from app.models.user import User
from app.schemas.rfq import RFQCreate


async def create_rfq(
    db: AsyncSession, data: RFQCreate, user: User
) -> RFQ:
    """Create RFQ with items. Generates reference_code."""
    # Generate reference code: RFQ-YYYY-NNNN
    year = datetime.now(timezone.utc).year
    count = await db.execute(
        select(func.count(RFQ.id)).where(
            RFQ.organization_id == user.organization_id
        )
    )
    seq = (count.scalar() or 0) + 1
    ref_code = f"RFQ-{year}-{seq:04d}"

    rfq = RFQ(
        organization_id=user.organization_id,
        reference_code=ref_code,
        title=data.title,
        description=data.description,
        client_id=data.client_id,
        created_by=user.id,
    )
    db.add(rfq)
    await db.flush()

    for i, item_data in enumerate(data.items):
        item = RFQItem(
            rfq_id=rfq.id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            sort_order=i,
        )
        db.add(item)

    await db.flush()
    return rfq


async def transition_rfq(
    db: AsyncSession, rfq_id: uuid.UUID, to_status: str, org_id: uuid.UUID
) -> RFQ:
    result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == org_id)
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    try:
        validate_rfq_transition(rfq.status, to_status)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    rfq.status = to_status
    await db.flush()
    return rfq
