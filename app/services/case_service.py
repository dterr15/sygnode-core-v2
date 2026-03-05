"""Case service — create cases, transitions, freeze with snapshot."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import calculate_pack_signature
from app.core.state_machines import validate_case_transition
from app.models.case import DecisionCase, CaseEvidence, CaseVersion
from app.models.user import User
from app.services.timeline_service import append_timeline_event


async def get_case_or_404(
    db: AsyncSession, case_id: uuid.UUID, org_id: uuid.UUID
) -> DecisionCase:
    result = await db.execute(
        select(DecisionCase).where(
            DecisionCase.id == case_id,
            DecisionCase.organization_id == org_id,
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return case


async def transition_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    to_status: str,
    user: User,
    notes: str | None = None,
) -> DecisionCase:
    """Transition case status. Only admin_org/master_admin allowed."""
    case = await get_case_or_404(db, case_id, user.organization_id)

    try:
        validate_case_transition(case.status, to_status, user.role)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if to_status == "FROZEN":
        # Must have at least 1 evidence
        ev_count = await db.execute(
            select(func.count(CaseEvidence.id)).where(CaseEvidence.case_id == case_id)
        )
        if ev_count.scalar() == 0:
            raise HTTPException(
                status_code=409, detail="No se puede congelar sin evidencias"
            )
        return await freeze_case(db, case, user, notes)

    case.status = to_status
    await db.flush()
    return case


async def freeze_case(
    db: AsyncSession,
    case: DecisionCase,
    user: User,
    notes: str | None = None,
) -> DecisionCase:
    """Freeze a case — create snapshot version."""
    case.status = "FROZEN"
    if not case.frozen_first_at:
        case.frozen_first_at = datetime.now(timezone.utc)
    case.current_version += 1

    # Create snapshot
    snapshot = {
        "case_id": str(case.id),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "version": case.current_version,
    }

    version = CaseVersion(
        case_id=case.id,
        version_number=case.current_version,
        snapshot_data=snapshot,
        frozen_by_user_id=user.id,
        frozen_by_role=user.role,
        notes=notes,
        integrity_hash=calculate_pack_signature(snapshot),
    )
    db.add(version)
    await db.flush()

    return case
