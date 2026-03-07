"""RFQ router — T8, T11."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.audit import EmailLog
from app.models.rfq import RFQ, RFQItem
from app.models.quote import Quote
from app.models.supplier import Supplier
from app.schemas.rfq import (
    RFQCreate, RFQUpdate, RFQOut, RFQItemOut,
    RFQAddSupplierRequest, RFQSendEmailsRequest, EmailLogOut,
    RFQItemSuppliersRequest,
)
from app.schemas.quote import QuoteOut
from app.schemas.pagination import CursorPage
from app.core.pagination import encode_cursor, apply_cursor_filter
from app.services.mailgun_service import mailgun_service
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
    email_logs_result = await db.execute(
        select(EmailLog)
        .where(EmailLog.rfq_id == rfq_id)
        .order_by(EmailLog.created_at.desc())
    )

    return {
        "rfq": RFQOut.model_validate(rfq),
        "items": [RFQItemOut.model_validate(i) for i in items_result.scalars().all()],
        "quotes": [QuoteOut.model_validate(q) for q in quotes_result.scalars().all()],
        "email_status": [EmailLogOut.model_validate(l) for l in email_logs_result.scalars().all()],
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


@router.post("/{rfq_id}/suppliers", status_code=201)
async def add_supplier_to_rfq(
    rfq_id: uuid.UUID,
    data: RFQAddSupplierRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Associate a supplier with this RFQ by creating a Quote placeholder. Idempotent."""
    # Verify RFQ belongs to the org
    rfq_result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    # Verify supplier belongs to the org
    supplier_result = await db.execute(
        select(Supplier).where(
            Supplier.id == data.supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    if not supplier_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    # Idempotent: return existing quote if already associated
    existing_result = await db.execute(
        select(Quote).where(Quote.rfq_id == rfq_id, Quote.supplier_id == data.supplier_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return {"quote_id": str(existing.id)}

    # Create placeholder Quote to establish the RFQ↔Supplier relationship
    await _ensure_quote_placeholder(db, rfq_id, data.supplier_id, current_user.organization_id)
    await db.commit()

    # Fetch the newly created quote to return its id
    quote_result = await db.execute(
        select(Quote).where(Quote.rfq_id == rfq_id, Quote.supplier_id == data.supplier_id)
    )
    quote = quote_result.scalar_one()
    return {"quote_id": str(quote.id)}


@router.post("/{rfq_id}/send-emails")
async def send_rfq_emails(
    rfq_id: uuid.UUID,
    data: RFQSendEmailsRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Send RFQ solicitation emails to the specified suppliers via Mailgun."""
    # Fetch RFQ (org check)
    rfq_result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    # Fetch RFQ items for items_html
    items_result = await db.execute(
        select(RFQItem).where(RFQItem.rfq_id == rfq_id).order_by(RFQItem.sort_order)
    )
    rfq_items = items_result.scalars().all()
    items_html = (
        "<ul>"
        + "".join(
            f"<li>{item.description} — {item.quantity} {item.unit}</li>"
            for item in rfq_items
        )
        + "</ul>"
    )

    sent_count = 0
    failed_count = 0
    details = []

    for supplier_id in data.supplier_ids:
        # Fetch supplier
        supplier_result = await db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.organization_id == current_user.organization_id,
            )
        )
        supplier = supplier_result.scalar_one_or_none()

        if not supplier:
            details.append({"supplier_id": str(supplier_id), "status": "skipped", "reason": "not_found"})
            continue

        if not supplier.email:
            details.append({"supplier_id": str(supplier_id), "status": "skipped", "reason": "no_email"})
            continue

        # Send email via Mailgun
        try:
            result = await mailgun_service.send_rfq_email(
                to_email=supplier.email,
                supplier_name=supplier.name,
                rfq_title=rfq.title,
                items_html=items_html,
            )
            message_id = result.get("id") or result.get("message-id")
            log = EmailLog(
                organization_id=current_user.organization_id,
                rfq_id=rfq_id,
                supplier_id=supplier_id,
                recipient_email=supplier.email,
                status="sent",
                message_id=message_id,
                sent_at=datetime.now(timezone.utc),
            )
            sent_count += 1
            details.append({"supplier_id": str(supplier_id), "status": "sent", "email": supplier.email})
        except Exception as exc:
            log = EmailLog(
                organization_id=current_user.organization_id,
                rfq_id=rfq_id,
                supplier_id=supplier_id,
                recipient_email=supplier.email,
                status="failed",
                error_message=str(exc),
            )
            failed_count += 1
            details.append({"supplier_id": str(supplier_id), "status": "failed", "error": str(exc)})

        db.add(log)

    await db.commit()
    return {"sent": sent_count, "failed": failed_count, "details": details}


async def _ensure_quote_placeholder(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    supplier_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> None:
    """Idempotently create a Quote placeholder linking supplier to RFQ."""
    existing = (await db.execute(
        select(Quote).where(Quote.rfq_id == rfq_id, Quote.supplier_id == supplier_id)
    )).scalar_one_or_none()
    if existing:
        return
    db.add(Quote(
        organization_id=organization_id,
        rfq_id=rfq_id,
        supplier_id=supplier_id,
        total_amount=Decimal("0"),
        status="pending",
    ))


@router.put("/{rfq_id}/items/{item_id}/suppliers")
async def set_item_suppliers(
    rfq_id: uuid.UUID,
    item_id: uuid.UUID,
    data: RFQItemSuppliersRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Set the supplier_ids for a specific RFQ item and upsert Quote placeholders."""
    # Verify RFQ belongs to org
    rfq_result = await db.execute(
        select(RFQ).where(RFQ.id == rfq_id, RFQ.organization_id == current_user.organization_id)
    )
    if not rfq_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="RFQ no encontrado")

    # Fetch the item and verify it belongs to this RFQ
    item_result = await db.execute(
        select(RFQItem).where(RFQItem.id == item_id, RFQItem.rfq_id == rfq_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")

    # Update supplier_ids on the item
    item.supplier_ids = list(data.supplier_ids)

    # Upsert Quote placeholder for each supplier (idempotent)
    for supplier_id in data.supplier_ids:
        await _ensure_quote_placeholder(
            db, rfq_id, supplier_id, current_user.organization_id
        )

    await db.commit()
    await db.refresh(item)
    return RFQItemOut.model_validate(item)


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
