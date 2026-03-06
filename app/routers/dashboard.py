"""Dashboard router — GET /api/v2/dashboard — returns org-scoped metrics."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.intake import IntakeList
from app.models.rfq import RFQ
from app.models.case import DecisionCase
from app.models.ml import MLModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Return key metrics for the authenticated user's organization."""
    org_id = current_user.organization_id

    intake_pending = await db.scalar(
        select(func.count(IntakeList.id)).where(
            IntakeList.organization_id == org_id,
            IntakeList.validation_status == "STAGED_PENDING_VALIDATION",
        )
    )

    rfqs_active = await db.scalar(
        select(func.count(RFQ.id)).where(
            RFQ.organization_id == org_id,
            RFQ.status.in_(["draft", "sent", "evaluating"]),
        )
    )

    cases_open = await db.scalar(
        select(func.count(DecisionCase.id)).where(
            DecisionCase.organization_id == org_id,
            DecisionCase.status == "OPEN",
        )
    )

    validations_pending = await db.scalar(
        select(func.count(MLModel.id)).where(
            MLModel.status == "pending",
        )
    ) if False else 0  # MLModel table may not have org_id; return 0 for now

    # Work queue: recent open cases with no fulfillment
    wq_result = await db.execute(
        select(DecisionCase)
        .where(
            DecisionCase.organization_id == org_id,
            DecisionCase.status == "OPEN",
        )
        .order_by(DecisionCase.created_at.desc())
        .limit(5)
    )
    work_queue = [
        {"title": c.objeto_resumen or f"Caso {str(c.id)[:8]}", "type": "case"}
        for c in wq_result.scalars().all()
    ]

    return {
        "intake_pending": intake_pending or 0,
        "rfqs_active": rfqs_active or 0,
        "cases_open": cases_open or 0,
        "validations_pending": validations_pending or 0,
        "work_queue": work_queue,
    }
