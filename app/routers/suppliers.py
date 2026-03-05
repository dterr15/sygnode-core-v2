"""Suppliers router — T19: scoring without N+1."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut, SupplierScore
from app.schemas.pagination import CursorPage
from app.core.pagination import encode_cursor, apply_cursor_filter
from app.services.scoring_service import score_suppliers, ScoringContext

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=CursorPage[SupplierOut])
async def list_suppliers(
    category: str | None = None,
    is_validated: bool | None = None,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Supplier).where(Supplier.organization_id == current_user.organization_id)
    if is_validated is not None:
        query = query.where(Supplier.is_validated == is_validated)
    if category:
        query = query.where(Supplier.categories.any(category))

    query = apply_cursor_filter(query, cursor, Supplier.id, Supplier.created_at)
    query = query.order_by(Supplier.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    items = result.scalars().all()

    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1].id, items[-1].created_at) if has_more and items else None

    return CursorPage(
        items=[SupplierOut.model_validate(s) for s in items],
        next_cursor=next_cursor,
    )


@router.post("", status_code=201)
async def create_supplier(
    data: SupplierCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    supplier = Supplier(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(supplier)
    await db.commit()
    return {"supplier": SupplierOut.model_validate(supplier)}


@router.get("/suggest")
async def suggest_suppliers(
    rfq_item_id: uuid.UUID | None = None,
    category: str = "",
    item_description: str = "",
    limit: int = Query(5, le=10),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T19: Suggest suppliers — single query, no N+1."""
    # Get all supplier IDs for this org
    result = await db.execute(
        select(Supplier.id).where(Supplier.organization_id == current_user.organization_id)
    )
    candidate_ids = [row[0] for row in result.fetchall()]

    context = ScoringContext(
        item_normalized=item_description.lower().strip(),
        category=category,
    )

    scores = await score_suppliers(
        db, current_user.organization_id, candidate_ids, context, limit
    )
    return {"suggestions": [s.model_dump() for s in scores]}


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return {"supplier": SupplierOut.model_validate(supplier)}


@router.patch("/{supplier_id}")
async def update_supplier(
    supplier_id: uuid.UUID,
    data: SupplierUpdate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    await db.commit()
    return {"supplier": SupplierOut.model_validate(supplier)}


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.organization_id == current_user.organization_id,
        )
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    await db.delete(supplier)
    await db.commit()
    return {"success": True}
