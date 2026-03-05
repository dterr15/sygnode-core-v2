"""Intake router — T4, T5, T6, T7."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.intake import IntakeList, IntakeItem
from app.schemas.intake import (
    IntakePasteRequest, IntakeApproveRequest, IntakeRejectRequest,
    IntakeTransitionRequest, IntakeItemUpdate,
    IntakeListOut, IntakeItemOut, IntakeDetailOut,
)
from app.schemas.pagination import CursorPage
from app.core.pagination import encode_cursor, apply_cursor_filter
from app.services.intake_service import (
    create_intake_from_paste, approve_intake, reject_intake, transition_intake,
)

router = APIRouter(prefix="/intake", tags=["intake"])


@router.get("", response_model=CursorPage[IntakeListOut])
async def list_intakes(
    status: str | None = None,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(IntakeList).where(
        IntakeList.organization_id == current_user.organization_id
    )
    if status:
        query = query.where(IntakeList.validation_status == status)

    query = apply_cursor_filter(query, cursor, IntakeList.id, IntakeList.created_at)
    query = query.order_by(IntakeList.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    items = result.scalars().all()

    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1].id, items[-1].created_at) if has_more and items else None

    return CursorPage(
        items=[IntakeListOut.model_validate(i) for i in items],
        next_cursor=next_cursor,
    )


@router.get("/{list_id}", response_model=IntakeDetailOut)
async def get_intake_detail(
    list_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    intake_result = await db.execute(
        select(IntakeList).where(
            IntakeList.id == list_id,
            IntakeList.organization_id == current_user.organization_id,
        )
    )
    intake = intake_result.scalar_one_or_none()
    if not intake:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lista no encontrada")

    items_result = await db.execute(
        select(IntakeItem).where(IntakeItem.list_id == list_id).order_by(IntakeItem.sort_order)
    )
    items = items_result.scalars().all()

    return IntakeDetailOut(
        list=IntakeListOut.model_validate(intake),
        items=[IntakeItemOut.model_validate(i) for i in items],
    )


@router.post("/paste", status_code=201)
async def paste_intake(
    data: IntakePasteRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T4: Paste text → create intake list with parsed items."""
    intake, item_count = await create_intake_from_paste(
        db, data.text, data.source, current_user, data.client_id
    )
    await db.commit()
    return {"list_id": intake.id, "item_count": item_count}


@router.post("/{list_id}/approve")
async def approve(
    list_id: uuid.UUID,
    data: IntakeApproveRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T6: Approve intake → create DecisionCase + first timeline event."""
    intake, case = await approve_intake(db, list_id, current_user, data.notes)
    await db.commit()
    return {"success": True, "case_id": case.id}


@router.post("/{list_id}/reject")
async def reject(
    list_id: uuid.UUID,
    data: IntakeRejectRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    await reject_intake(db, list_id, current_user, data.reason)
    await db.commit()
    return {"success": True}


@router.post("/{list_id}/transition")
async def transition(
    list_id: uuid.UUID,
    data: IntakeTransitionRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T7: Invalid transitions return 409."""
    try:
        intake = await transition_intake(db, list_id, data.to_status, current_user)
        await db.commit()
        return {"id": intake.id, "status": intake.status}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{list_id}/items/{item_id}")
async def update_intake_item(
    list_id: uuid.UUID,
    item_id: uuid.UUID,
    data: IntakeItemUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntakeItem).where(IntakeItem.id == item_id, IntakeItem.list_id == list_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Ítem no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    return {"item": IntakeItemOut.model_validate(item)}
