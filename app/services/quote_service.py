"""Quote service — create quotes with items."""

import uuid
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.state_machines import validate_quote_transition
from app.models.quote import Quote, QuoteItem
from app.models.user import User
from app.schemas.quote import QuoteCreate


async def create_quote(
    db: AsyncSession, rfq_id: uuid.UUID, data: QuoteCreate, user: User
) -> Quote:
    quote = Quote(
        organization_id=user.organization_id,
        rfq_id=rfq_id,
        supplier_id=data.supplier_id,
        total_amount=data.total_amount,
        freight_total=data.freight_total,
        currency=data.currency,
        payment_condition=data.payment_condition,
        delivery_time_days=data.delivery_time_days,
        valid_until=data.valid_until,
    )
    db.add(quote)
    await db.flush()

    for item_data in data.items:
        item = QuoteItem(
            quote_id=quote.id,
            rfq_item_id=item_data.rfq_item_id,
            description=item_data.description,
            unit_price=item_data.unit_price,
            quantity=item_data.quantity,
            unit=item_data.unit,
            match_confidence=item_data.match_confidence,
            extracted_by_ai=item_data.extracted_by_ai,
        )
        db.add(item)

    await db.flush()
    return quote


async def transition_quote(
    db: AsyncSession, quote_id: uuid.UUID, to_status: str, org_id: uuid.UUID
) -> Quote:
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id, Quote.organization_id == org_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    try:
        validate_quote_transition(quote.status, to_status)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    quote.status = to_status
    await db.flush()
    return quote
