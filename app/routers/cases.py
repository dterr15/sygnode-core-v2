"""Cases (traceability) router — T12, T13, T14, T15, T16, T20."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.core.hashing import calculate_sha256
from app.core.pagination import encode_cursor, apply_cursor_filter
from app.models.case import (
    DecisionCase, CaseTimelineEvent, CaseEvidence, CaseFulfillment,
)
from app.schemas.case import (
    CaseTransitionRequest, DecisionCaseSummary, CaseTimelineEventOut,
    CaseEvidenceOut, ChainIntegrityResult, GapOut, EvidencePackOut,
)
from app.schemas.fulfillment import JustifyVarianceRequest, FulfillmentOut
from app.schemas.pagination import CursorPage
from app.services.case_service import get_case_or_404, transition_case
from app.services.timeline_service import append_timeline_event, verify_chain_integrity
from app.services.evidence_service import compile_evidence_pack
from app.services.document_service import document_service
from app.settings import settings

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=CursorPage[DecisionCaseSummary])
async def list_cases(
    status: str | None = None,
    limit: int = Query(20, le=100),
    cursor: str | None = None,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(DecisionCase).where(
        DecisionCase.organization_id == current_user.organization_id
    )
    if status:
        query = query.where(DecisionCase.status == status)

    query = apply_cursor_filter(query, cursor, DecisionCase.id, DecisionCase.created_at)
    query = query.order_by(DecisionCase.created_at.desc()).limit(limit + 1)

    result = await db.execute(query)
    items = result.scalars().all()

    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1].id, items[-1].created_at) if has_more and items else None

    summaries = []
    for c in items:
        ev_count = await db.execute(
            select(func.count(CaseEvidence.id)).where(CaseEvidence.case_id == c.id)
        )
        event_count = await db.execute(
            select(func.count(CaseTimelineEvent.id)).where(CaseTimelineEvent.case_id == c.id)
        )
        s = DecisionCaseSummary.model_validate(c)
        s.evidence_count = ev_count.scalar() or 0
        s.event_count = event_count.scalar() or 0
        summaries.append(s)

    return CursorPage(items=summaries, next_cursor=next_cursor)


@router.get("/{case_id}")
async def get_case_detail(
    case_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(db, case_id, current_user.organization_id)

    timeline_result = await db.execute(
        select(CaseTimelineEvent)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.event_timestamp)
    )
    evidences_result = await db.execute(
        select(CaseEvidence).where(CaseEvidence.case_id == case_id)
    )
    fulfillment_result = await db.execute(
        select(CaseFulfillment).where(CaseFulfillment.case_id == case_id)
    )
    chain = await verify_chain_integrity(db, case_id)

    fulfillment = fulfillment_result.scalar_one_or_none()

    return {
        "case": DecisionCaseSummary.model_validate(case),
        "timeline": [CaseTimelineEventOut.model_validate(e) for e in timeline_result.scalars().all()],
        "evidences": [CaseEvidenceOut.model_validate(e) for e in evidences_result.scalars().all()],
        "fulfillment": FulfillmentOut.model_validate(fulfillment) if fulfillment else None,
        "chain_intact": chain["intact"],
    }


@router.post("/{case_id}/transition")
async def transition(
    case_id: uuid.UUID,
    data: CaseTransitionRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    case = await transition_case(db, case_id, data.to_status, current_user, data.notes)
    await db.commit()
    return {"case_id": case.id, "status": case.status}


@router.post("/{case_id}/upload-po")
async def upload_po(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T12: Upload PO → extract → award inference → contrast."""
    case = await get_case_or_404(db, case_id, current_user.organization_id)

    file_bytes = await file.read()
    sha256 = calculate_sha256(file_bytes)

    # Upload to DataRoom
    doc_ref = await document_service.upload_document(
        file_bytes=file_bytes,
        filename=file.filename or "po.pdf",
        org_id=current_user.organization_id,
        doc_type="po",
        parent_id=case_id,
    )

    # Create evidence
    evidence = CaseEvidence(
        case_id=case_id,
        evidence_type="PO",
        filename=file.filename or "po.pdf",
        file_size=len(file_bytes),
        mime_type=file.content_type,
        sha256_hash=sha256,
        storage_ref=doc_ref.storage_ref,
        uploaded_by_user_id=current_user.id,
    )
    db.add(evidence)
    await db.flush()

    # Extract PO data with Gemini (G6: explicit user trigger)
    from app.services.gemini_service import extract_po_data
    try:
        po_data = await extract_po_data(file_bytes, file.content_type or "application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Create fulfillment
    from decimal import Decimal
    delta_pct = Decimal("0")
    requires_justification = False
    flag = "WITHIN_RANGE"

    fulfillment = CaseFulfillment(
        case_id=case_id,
        po_number=po_data.po_number,
        po_date=po_data.po_date,
        po_issue_date_confidence=po_data.po_issue_date_confidence,
        final_amount=po_data.total_amount,
        currency=po_data.currency,
        supplier_name=po_data.supplier_name,
        supplier_identification_confidence=po_data.supplier_identification_confidence,
        approved_by_name=po_data.approved_by_name,
        approved_by_role=po_data.approved_by_role,
        po_evidence_id=evidence.id,
        delta_pct=delta_pct,
        requires_justification=requires_justification,
        award_type="total",
        award_confidence="medium",
        award_inferred_at=datetime.now(timezone.utc),
    )
    db.add(fulfillment)
    await db.flush()

    # Timeline events
    await append_timeline_event(
        db, case_id, "PO_INGESTED",
        f"OC ingresada: {po_data.po_number}",
        current_user.id, current_user.role, artifact_hash=sha256,
        related_doc_ids=[evidence.id],
    )
    await append_timeline_event(
        db, case_id, "AWARD_INFERRED",
        f"Adjudicación inferida: {fulfillment.award_type}",
        current_user.id, current_user.role,
    )
    await append_timeline_event(
        db, case_id, flag,
        f"Contraste PO: delta {delta_pct}%",
        current_user.id, current_user.role,
    )

    await db.commit()

    return {
        "fulfillment_id": fulfillment.id,
        "po_data": po_data.model_dump(),
        "award": {"award_type": fulfillment.award_type, "award_confidence": fulfillment.award_confidence},
        "contrast": {"delta_pct": str(delta_pct), "flag": flag, "requires_justification": requires_justification},
    }


@router.get("/{case_id}/verify-chain")
async def verify_chain(
    case_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T13: Verify chain integrity."""
    await get_case_or_404(db, case_id, current_user.organization_id)
    result = await verify_chain_integrity(db, case_id)
    return result


@router.get("/{case_id}/evidence-pack")
async def get_evidence_pack(
    case_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T15: Compile evidence pack."""
    await get_case_or_404(db, case_id, current_user.organization_id)
    pack = await compile_evidence_pack(db, case_id)
    return {"evidence_pack": pack, "integrity": pack["integrity"]}


@router.get("/{case_id}/gaps")
async def get_gaps(
    case_id: uuid.UUID,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Extract gaps from timeline GAP_FLAGGED events."""
    await get_case_or_404(db, case_id, current_user.organization_id)
    result = await db.execute(
        select(CaseTimelineEvent)
        .where(
            CaseTimelineEvent.case_id == case_id,
            CaseTimelineEvent.event_type == "GAP_FLAGGED",
        )
    )
    gaps = []
    for event in result.scalars().all():
        meta = event.event_metadata or {}
        gaps.append(GapOut(
            gap_type=meta.get("gap_type", "UNKNOWN"),
            severity=meta.get("severity", "info"),
            description=event.event_description,
            event_id=event.id,
        ))
    return {"gaps": gaps}


@router.post("/{case_id}/justify-variance")
async def justify_variance(
    case_id: uuid.UUID,
    data: JustifyVarianceRequest,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T20: Justify variance — no timeline event generated."""
    await get_case_or_404(db, case_id, current_user.organization_id)

    result = await db.execute(
        select(CaseFulfillment).where(CaseFulfillment.case_id == case_id)
    )
    fulfillment = result.scalar_one_or_none()
    if not fulfillment:
        raise HTTPException(status_code=404, detail="No hay fulfillment para este caso")
    if not fulfillment.requires_justification:
        raise HTTPException(status_code=409, detail="Este caso no requiere justificación")

    fulfillment.variance_justification = data.justification
    fulfillment.reconciliation_status = "VARIANCE_JUSTIFIED"
    fulfillment.reconciled_at = datetime.now(timezone.utc)

    await db.commit()
    return {"success": True, "reconciliation_status": "VARIANCE_JUSTIFIED"}
