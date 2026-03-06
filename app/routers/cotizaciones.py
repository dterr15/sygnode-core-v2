"""Cotizaciones router — T9, T10: upload + Gemini processing."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.core.hashing import calculate_sha256
from app.models.case import DecisionCase, CaseEvidence
from app.services.document_service import document_service
from app.services.timeline_service import append_timeline_event
from app.settings import settings

router = APIRouter(prefix="/cotizaciones", tags=["cotizaciones"])


@router.post("/upload", status_code=201)
async def upload_cotizacion(
    file: UploadFile = File(...),
    rfq_id: uuid.UUID = Form(...),
    supplier_id: uuid.UUID = Form(...),
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T9: Upload quote PDF, store in DataRoom, create evidence + timeline event."""
    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Archivo demasiado grande (max {settings.max_upload_size_mb}MB)")

    sha256 = calculate_sha256(file_bytes)

    # Upload to DataRoom NAS
    doc_ref = await document_service.upload_document(
        file_bytes=file_bytes,
        filename=file.filename or "cotizacion.pdf",
        org_id=current_user.organization_id,
        doc_type="rfq",
        parent_id=rfq_id,
        supplier_id=supplier_id,
    )

    # Look for existing case linked to this RFQ
    case_result = await db.execute(
        select(DecisionCase).where(
            DecisionCase.organization_id == current_user.organization_id,
            DecisionCase.primary_rfq_id == rfq_id,
        )
    )
    case = case_result.scalar_one_or_none()

    # Always create evidence (case_id nullable for pre-case uploads)
    evidence = CaseEvidence(
        case_id=case.id if case else None,
        evidence_type="QUOTE",
        filename=file.filename or "cotizacion.pdf",
        file_size=len(file_bytes),
        mime_type=file.content_type,
        sha256_hash=sha256,
        storage_ref=doc_ref.storage_ref,
        uploaded_by_user_id=current_user.id,
    )
    db.add(evidence)
    await db.flush()

    if case:
        await append_timeline_event(
            db=db,
            case_id=case.id,
            event_type="EVIDENCE_UPLOADED",
            description=f"Cotización subida: {file.filename}",
            actor_user_id=current_user.id,
            actor_role=current_user.role,
            artifact_hash=sha256,
            related_doc_ids=[evidence.id],
        )

    await db.commit()

    return {
        "document_id": evidence.id,
        "filename": file.filename,
        "storage_ref": doc_ref.storage_ref,
        "sha256": sha256,
    }


@router.post("/{document_id}/process")
async def process_cotizacion(
    document_id: uuid.UUID,
    body: dict,
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """T10: Process quote with Gemini — G6: explicit trigger."""
    from app.services.gemini_service import extract_quote_from_document
    import json

    # Get evidence to find storage_ref
    evidence_result = await db.execute(
        select(CaseEvidence).where(CaseEvidence.id == document_id)
    )
    evidence = evidence_result.scalar_one_or_none()
    if not evidence:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    try:
        file_bytes = await document_service.get_document_bytes(evidence.storage_ref)
    except Exception:
        raise HTTPException(status_code=422, detail="No se pudo acceder al documento")

    rfq_items = body.get("rfq_items", [])
    schema_json = json.dumps({"type": "object"})  # Simplified schema reference

    try:
        extraction = await extract_quote_from_document(
            file_bytes=file_bytes,
            mime_type=evidence.mime_type or "application/pdf",
            rfq_items_json=json.dumps(rfq_items, default=str),
            schema_json=schema_json,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Update evidence with extracted data
    evidence.extracted_data = extraction.model_dump()
    evidence.extraction_confidence = extraction.items[0].match_confidence if extraction.items else 0
    await db.commit()

    return {
        "extracted": extraction.model_dump(),
        "items_matched": [item.model_dump() for item in extraction.items],
    }
