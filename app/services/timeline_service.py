"""
Timeline Service — G1: Trazabilidad Inviolable.
Append-only events with SHA256 chain.
NEVER update or delete events.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import calculate_event_hash
from app.models.case import CaseTimelineEvent


async def get_prev_hash(db: AsyncSession, case_id: uuid.UUID) -> str:
    """Get hash of the last event in the case timeline. Returns 'GENESIS' if no events."""
    result = await db.execute(
        select(CaseTimelineEvent.event_hash)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.event_timestamp.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row else "GENESIS"


async def append_timeline_event(
    db: AsyncSession,
    case_id: uuid.UUID,
    event_type: str,
    description: str,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    metadata: dict | None = None,
    artifact_hash: str | None = None,
    related_doc_ids: list[uuid.UUID] | None = None,
) -> CaseTimelineEvent:
    """
    Append a new event to the case timeline.
    Calculates event_hash from SHA256 chain.
    NEVER updates or deletes — INSERT only (G1).
    """
    event_id = uuid.uuid4()
    event_timestamp = datetime.now(timezone.utc)

    # 1. Get hash of previous event (or GENESIS)
    prev_hash = await get_prev_hash(db, case_id)

    # 2. Calculate event hash using the chain formula from doc 03
    event_hash = calculate_event_hash(
        event_id=event_id,
        case_id=case_id,
        event_type=event_type,
        event_timestamp=event_timestamp,
        actor_role=actor_role,
        related_doc_ids=related_doc_ids,
        artifact_hash=artifact_hash,
        prev_event_hash=prev_hash,
    )

    # 3. INSERT — never UPDATE
    event = CaseTimelineEvent(
        id=event_id,
        case_id=case_id,
        event_type=event_type,
        event_description=description,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        event_metadata=metadata,
        event_timestamp=event_timestamp,
        prev_event_hash=prev_hash,
        event_hash=event_hash,
        artifact_hash=artifact_hash,
        related_doc_ids=related_doc_ids or [],
    )
    db.add(event)
    await db.flush()

    return event


async def verify_chain_integrity(
    db: AsyncSession, case_id: uuid.UUID
) -> dict:
    """
    Verify the SHA256 chain of a case's timeline.
    Returns {intact: bool, total_events: int, broken_at: UUID|None}
    """
    result = await db.execute(
        select(CaseTimelineEvent)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.event_timestamp)
    )
    events = result.scalars().all()

    if not events:
        return {"intact": True, "total_events": 0, "broken_at": None}

    prev_hash = "GENESIS"
    for event in events:
        if event.prev_event_hash != prev_hash:
            return {
                "intact": False,
                "total_events": len(events),
                "broken_at": event.id,
            }

        # Recalculate hash to verify integrity
        expected_hash = calculate_event_hash(
            event_id=event.id,
            case_id=event.case_id,
            event_type=event.event_type,
            event_timestamp=event.event_timestamp,
            actor_role=event.actor_role,
            related_doc_ids=event.related_doc_ids,
            artifact_hash=event.artifact_hash,
            prev_event_hash=event.prev_event_hash,
        )
        if event.event_hash != expected_hash:
            return {
                "intact": False,
                "total_events": len(events),
                "broken_at": event.id,
            }

        prev_hash = event.event_hash

    return {"intact": True, "total_events": len(events), "broken_at": None}
