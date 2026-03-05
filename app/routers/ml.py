"""ML router — stats and retrain."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.services.ml_service import get_ml_stats

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/stats")
async def ml_stats(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_ml_stats(db)


@router.post("/retrain")
async def ml_retrain(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    # Placeholder for scikit-learn retraining
    return {"success": True, "new_stats": await get_ml_stats(db)}
