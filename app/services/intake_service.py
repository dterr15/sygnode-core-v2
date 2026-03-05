"""
Intake service — handles paste parsing, approval, rejection.
G3: validated_by_user_id only set with authenticated user.
R5: State machine transitions validated.
"""

import hashlib
import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.state_machines import (
    validate_intake_validation_transition,
    validate_intake_status_transition,
)
from app.models.intake import IntakeList, IntakeItem
from app.models.case import DecisionCase
from app.models.user import User
from app.services.timeline_service import append_timeline_event


async def create_intake_from_paste(
    db: AsyncSession,
    text: str,
    source: str,
    user: User,
    client_id: uuid.UUID | None = None,
) -> tuple[IntakeList, int]:
    """Parse text and create intake list with items."""
    # Deduplication check
    paste_hash = hashlib.sha256(text.strip().encode()).hexdigest()
    existing = await db.execute(
        select(IntakeList).where(
            IntakeList.organization_id == user.organization_id,
            IntakeList.paste_hash == paste_hash,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Contenido duplicado",
        )

    # Parse items from text
    items_data = parse_text_to_items(text)
    if not items_data:
        raise HTTPException(status_code=400, detail="Texto vacío o insuficiente")

    # Create intake list
    intake = IntakeList(
        organization_id=user.organization_id,
        status="PENDIENTE_REVISION",
        validation_status="STAGED_PENDING_VALIDATION",
        title=_generate_title(text),
        source=source,
        paste_hash=paste_hash,
        context_body=text,
        client_id=client_id,
    )
    db.add(intake)
    await db.flush()

    # Create items
    for i, item_data in enumerate(items_data):
        item = IntakeItem(
            list_id=intake.id,
            description=item_data["description"],
            quantity=item_data.get("quantity"),
            uom=item_data.get("uom", "un"),
            confidence_score=item_data.get("confidence", 0.7),
            needs_clarification=item_data.get("needs_clarification", False),
            original_text=item_data.get("original_text"),
            sort_order=i,
        )
        db.add(item)

    await db.flush()
    return intake, len(items_data)


async def approve_intake(
    db: AsyncSession,
    list_id: uuid.UUID,
    user: User,
    notes: str | None = None,
) -> tuple[IntakeList, DecisionCase]:
    """
    Approve an intake list — G3: validated_by_user_id set with real user.
    Creates a DecisionCase and first timeline event.
    """
    intake = await _get_intake_or_404(db, list_id, user.organization_id)

    if intake.validation_status != "STAGED_PENDING_VALIDATION":
        raise HTTPException(status_code=409, detail="Ya fue aprobada o rechazada")

    # Validate transition (R5)
    validate_intake_validation_transition(
        intake.validation_status, "APPROVED_GENERATED"
    )

    # G3: Only set with real authenticated user
    intake.validation_status = "APPROVED_GENERATED"
    intake.validated_by_user_id = user.id
    intake.validated_at = datetime.now(timezone.utc)
    intake.status = "PENDIENTE_REVISION"

    # Create DecisionCase
    case = DecisionCase(
        organization_id=user.organization_id,
        intake_list_id=intake.id,
        status="OPEN",
    )
    db.add(case)
    await db.flush()

    # First timeline event
    await append_timeline_event(
        db=db,
        case_id=case.id,
        event_type="CASE_CREATED",
        description=f"Caso creado desde intake '{intake.title}'",
        actor_user_id=user.id,
        actor_role=user.role,
        metadata={"notes": notes, "intake_list_id": str(intake.id)},
    )

    await db.flush()
    return intake, case


async def reject_intake(
    db: AsyncSession,
    list_id: uuid.UUID,
    user: User,
    reason: str,
) -> IntakeList:
    """Reject an intake list."""
    intake = await _get_intake_or_404(db, list_id, user.organization_id)

    if intake.validation_status != "STAGED_PENDING_VALIDATION":
        raise HTTPException(status_code=409, detail="Ya fue aprobada o rechazada")

    validate_intake_validation_transition(
        intake.validation_status, "REJECTED_MIN_DATA_PENDING"
    )

    intake.validation_status = "REJECTED_MIN_DATA_PENDING"
    intake.validated_by_user_id = user.id
    intake.validated_at = datetime.now(timezone.utc)
    intake.rejected_reason = reason

    await db.flush()
    return intake


async def transition_intake(
    db: AsyncSession,
    list_id: uuid.UUID,
    to_status: str,
    user: User,
) -> IntakeList:
    """Transition intake list status (operational status, not validation)."""
    intake = await _get_intake_or_404(db, list_id, user.organization_id)

    validate_intake_status_transition(intake.status, to_status)

    intake.status = to_status
    await db.flush()
    return intake


def parse_text_to_items(text: str) -> list[dict]:
    """
    Skill 1: parse_intake_text — regex-based parsing.
    Extracts items with quantity and unit from free text.
    """
    items = []
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    qty_pattern = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(kg|lt|m2|m|un|caja|paq|gl|ton|sacos?|unidades?|litros?|metros?)\b",
        re.IGNORECASE,
    )

    uom_map = {
        "saco": "saco", "sacos": "saco",
        "unidad": "un", "unidades": "un",
        "litro": "lt", "litros": "lt",
        "metro": "m", "metros": "m",
    }

    for line in lines:
        match = qty_pattern.search(line)
        if match:
            qty_str = match.group(1).replace(",", ".")
            raw_uom = match.group(2).lower()
            uom = uom_map.get(raw_uom, raw_uom)
            # Description is everything except the matched quantity+unit
            desc = qty_pattern.sub("", line).strip(" -·•,")
            if not desc:
                desc = line
            items.append({
                "description": desc,
                "quantity": float(qty_str),
                "uom": uom,
                "confidence": 0.85,
                "needs_clarification": False,
                "original_text": line,
            })
        else:
            # No quantity detected — still add as item
            items.append({
                "description": line.strip(" -·•,"),
                "quantity": None,
                "uom": "un",
                "confidence": 0.5,
                "needs_clarification": True,
                "original_text": line,
            })

    return items


def _generate_title(text: str) -> str:
    """Generate a short title from the first line of text."""
    first_line = text.strip().split("\n")[0][:100]
    return first_line if first_line else "Lista sin título"


async def _get_intake_or_404(
    db: AsyncSession, list_id: uuid.UUID, org_id: uuid.UUID
) -> IntakeList:
    result = await db.execute(
        select(IntakeList).where(
            IntakeList.id == list_id,
            IntakeList.organization_id == org_id,
        )
    )
    intake = result.scalar_one_or_none()
    if not intake:
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    return intake
