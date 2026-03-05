"""Freight router."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.system import SkuFreightMaster

router = APIRouter(prefix="/freight", tags=["freight"])


@router.get("/master")
async def get_freight_master(
    skus: str = Query(""),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    sku_list = [s.strip() for s in skus.split(",") if s.strip()]
    query = select(SkuFreightMaster).where(
        SkuFreightMaster.organization_id == current_user.organization_id
    )
    if sku_list:
        query = query.where(SkuFreightMaster.sku_description.in_(sku_list))

    result = await db.execute(query)
    items = result.scalars().all()
    return {"items": [
        {
            "sku_description": f.sku_description,
            "supplier_id": str(f.supplier_id),
            "unit_freight_cost": float(f.unit_freight_cost),
        }
        for f in items
    ]}
