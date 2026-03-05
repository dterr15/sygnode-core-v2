"""Public endpoints — no authentication required."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.case import DecisionCase, CaseTimelineEvent
from app.services.timeline_service import verify_chain_integrity

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/verify/{case_id}")
async def public_verify(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """T16: Public verification endpoint — no auth required."""
    result = await db.execute(
        select(DecisionCase).where(DecisionCase.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado o no publicado")

    chain = await verify_chain_integrity(db, case_id)

    # Get chain anchor (last event hash)
    last_event = await db.execute(
        select(CaseTimelineEvent.event_hash)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.event_timestamp.desc())
        .limit(1)
    )
    anchor = last_event.scalar_one_or_none() or "GENESIS"

    return {
        "case_id": case_id,
        "integrity_status": "VERIFIED" if chain["intact"] else "TAMPERED",
        "chain_anchor": anchor,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
