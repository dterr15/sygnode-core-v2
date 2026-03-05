"""Clients router — CRUD."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientOut
from app.schemas.pagination import CursorPage
from app.core.pagination import encode_cursor, apply_cursor_filter

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=CursorPage[ClientOut])
async def list_clients(
    archived: bool = False,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Client).where(
        Client.organization_id == current_user.organization_id,
        Client.archived == archived,
    )
    query = apply_cursor_filter(query, cursor, Client.id, Client.created_at)
    query = query.order_by(Client.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    items = result.scalars().all()

    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1].id, items[-1].created_at) if has_more and items else None

    return CursorPage(
        items=[ClientOut.model_validate(c) for c in items],
        next_cursor=next_cursor,
    )


@router.post("", status_code=201)
async def create_client(
    data: ClientCreate,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    # Check RUT uniqueness within org
    existing = await db.execute(
        select(Client).where(
            Client.organization_id == current_user.organization_id,
            Client.rut == data.rut,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="RUT ya registrado en esta organización")

    client = Client(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(client)
    await db.commit()
    return {"client": ClientOut.model_validate(client)}


@router.get("/{client_id}")
async def get_client(
    client_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.organization_id == current_user.organization_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"client": ClientOut.model_validate(client)}
