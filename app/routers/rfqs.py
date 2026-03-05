"""RFQ router — T8, T11."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.rfq import RFQ, RFQItem
from app.models.quote import Quote
from app.schemas.rfq import RFQCreate, RFQUpdate, RFQOut, RFQItemOut
from app.schemas.quote import QuoteOut
from app.schemas.pagination import CursorPage
from app.core.pagination import encode_cursor, apply_cursor_filter
from app.services.rfq_service import create_rfq, transition_rfq

router = APIRouter(prefix="/rfqs", tags=["rfqs"])


@router.get("", response_model=CursorPage[RFQOut])
async def list_rfqs(
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T3: Only returns RFQs from user's organization."""
    query = select(RFQ).where(RFQ.organization_id == current_user.organization_id)
    if status:
        query = query.where(RFQ.status == status)
    if client_id:
        query = query.where(RFQ.client_id == client_id)

    query = apply_cursor_filter(query, cursor, RFQ.id, RFQ.created_at)
    query = query.order_by(RFQ.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    items = result.scalars().all()

    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1].id, items[-1].created_at) if has_more and items else None

    return CursorPage(
        items=[RFQOut.model_validate(r) for r in items],
        next_cursor=next_cursor,
    )


@router.post("", status_code=201)
async def create_rfq_endpoint(
    data: RFQCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T8: Create RFQ with items, returns reference_code."""
    rfq = await create_rfq(db, data, current_user)
    await db.commit()
    return {"rfq": RFQOut.model_validate(rfq)}


@router.get("/{rfq_id}")
async def get_rfq_detail(
    rfq_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    rfq_result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    items_result = await db.execute(
        select(RFQItem).where(RFQItem.rfq_id == rfq_id).order_by(RFQItem.sort_order)
    )
    quotes_result = await db.execute(select(Quote).where(Quote.rfq_id == rfq_id))

    return {
        "rfq": RFQOut.model_validate(rfq),
        "items": [RFQItemOut.model_validate(i) for i in items_result.scalars().all()],
        "quotes": [QuoteOut.model_validate(q) for q in quotes_result.scalars().all()],
        "email_status": [],
    }


@router.patch("/{rfq_id}")
async def update_rfq(
    rfq_id: uuid.UUID,
    data: RFQUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data and update_data["status"] != rfq.status:
        try:
            from app.core.state_machines import validate_rfq_transition
            validate_rfq_transition(rfq.status, update_data["status"])
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    for field, value in update_data.items():
        setattr(rfq, field, value)

    await db.commit()
    return {"rfq": RFQOut.model_validate(rfq)}


@router.delete("/{rfq_id}")
async def delete_rfq(
    rfq_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")
    await db.delete(rfq)
    await db.commit()
    return {"success": True}


@router.post("/{rfq_id}/analyze")
async def analyze_rfq(
    rfq_id: uuid.UUID,
    body: dict,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T11: Analyze quotes — G6: explicit trigger only."""
    from app.services.gemini_service import generate_comparative_analysis

    rfq_result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    analysis = await generate_comparative_analysis(
        rfq_title=rfq.title,
        items_summary=body.get("items_summary", {}),
        context=body.get("context", ""),
    )

    return {"analysis": analysis.model_dump()}
