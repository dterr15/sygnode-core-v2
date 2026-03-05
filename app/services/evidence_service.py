"""Evidence service — compile and verify Evidence Pack (Skill 7)."""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import calculate_pack_signature
from app.models.case import (
    DecisionCase, CaseTimelineEvent, CaseEvidence,
    CaseVersion, CaseFulfillment,
)
from app.services.timeline_service import verify_chain_integrity


async def compile_evidence_pack(db: AsyncSession, case_id: uuid.UUID) -> dict:
    """
    Skill 7: compile_evidence_pack.
    Compiles and verifies the Evidence Pack for audit.
    Precondition: case.frozen_first_at IS NOT NULL.
    """
    # 1. Get case
    case_result = await db.execute(
        select(DecisionCase).where(DecisionCase.id == case_id)
    )
    case = case_result.scalar_one()

    # 2. Get timeline ordered
    timeline_result = await db.execute(
        select(CaseTimelineEvent)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.event_timestamp)
    )
    timeline = timeline_result.scalars().all()

    # 3. Get evidences
    evidences_result = await db.execute(
        select(CaseEvidence).where(CaseEvidence.case_id == case_id)
    )
    evidences = evidences_result.scalars().all()

    # 4. Get fulfillment
    fulfillment_result = await db.execute(
        select(CaseFulfillment).where(CaseFulfillment.case_id == case_id)
    )
    fulfillment = fulfillment_result.scalar_one_or_none()

    # 5. Get versions
    versions_result = await db.execute(
        select(CaseVersion)
        .where(CaseVersion.case_id == case_id)
        .order_by(CaseVersion.version_number)
    )
    versions = versions_result.scalars().all()

    # 6. Verify chain integrity
    integrity = await verify_chain_integrity(db, case_id)

    # 7. Build pack data
    pack_data = {
        "case_id": str(case.id),
        "organization_id": str(case.organization_id),
        "status": case.status,
        "timeline": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "event_description": e.event_description,
                "event_timestamp": e.event_timestamp.isoformat(),
                "event_hash": e.event_hash,
                "prev_event_hash": e.prev_event_hash,
            }
            for e in timeline
        ],
        "evidences": [
            {
                "id": str(e.id),
                "evidence_type": e.evidence_type,
                "filename": e.filename,
                "sha256_hash": e.sha256_hash,
            }
            for e in evidences
        ],
        "fulfillment": {
            "po_number": fulfillment.po_number,
            "final_amount": str(fulfillment.final_amount),
            "delta_pct": str(fulfillment.delta_pct) if fulfillment.delta_pct else None,
            "reconciliation_status": fulfillment.reconciliation_status,
        } if fulfillment else None,
        "integrity": integrity,
    }

    pack_data["pack_signature"] = calculate_pack_signature(pack_data)

    return pack_data
