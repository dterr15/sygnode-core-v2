"""Validations router — pending ML validations."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser

router = APIRouter(prefix="/validations", tags=["validations"])


@router.get("")
async def list_validations(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    # Pending validations for ML-inferred data
    return {"items": [], "next_cursor": None}
