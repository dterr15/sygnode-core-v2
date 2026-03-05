"""ML service — scikit-learn model for supplier scoring (ADR-004)."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml import MLModel


async def get_active_model(db: AsyncSession) -> MLModel | None:
    result = await db.execute(
        select(MLModel).where(MLModel.is_active == True).limit(1)
    )
    return result.scalar_one_or_none()


async def get_ml_stats(db: AsyncSession) -> dict:
    model = await get_active_model(db)
    if not model:
        return {
            "model_version": 0,
            "accuracy": 0,
            "precision": 0,
            "recall": 0,
            "f1": 0,
            "samples_trained": 0,
            "trained_at": None,
            "status": "no_model",
        }
    return {
        "model_version": 1,
        "accuracy": float(model.accuracy or 0),
        "precision": float(model.precision_score or 0),
        "recall": float(model.recall or 0),
        "f1": float(model.f1_score or 0),
        "samples_trained": model.samples_trained or 0,
        "trained_at": model.trained_at.isoformat() if model.trained_at else None,
        "status": "active",
    }
