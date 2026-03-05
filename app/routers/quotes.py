"""Quotes router."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.quote import Quote
from app.schemas.quote import QuoteCreate, QuoteOut
from app.services.quote_service import create_quote

router = APIRouter(tags=["quotes"])


@router.get("/rfqs/{rfq_id}/quotes")
async def list_quotes(
    rfq_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Quote).where(
            Quote.rfq_id == rfq_id,
            Quote.organization_id == current_user.organization_id,
        )
    )
    return {"quotes": [QuoteOut.model_validate(q) for q in result.scalars().all()]}


@router.post("/rfqs/{rfq_id}/quotes", status_code=201)
async def create_quote_endpoint(
    rfq_id: uuid.UUID,
    data: QuoteCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    quote = await create_quote(db, rfq_id, data, current_user)
    await db.commit()
    return {"quote": QuoteOut.model_validate(quote)}
