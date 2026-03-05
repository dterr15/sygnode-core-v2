from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class CaseTransitionRequest(BaseModel):
    to_status: str
    notes: str | None = None


class CaseTimelineEventOut(BaseModel):
    id: UUID
    case_id: UUID
    event_type: str
    event_description: str
    actor_user_id: UUID | None = None
    actor_role: str | None = None
    event_metadata: dict | None = None
    event_timestamp: datetime
    prev_event_hash: str
    event_hash: str
    artifact_hash: str | None = None
    related_doc_ids: list[UUID]

    model_config = {"from_attributes": True}


class CaseEvidenceOut(BaseModel):
    id: UUID
    case_id: UUID
    evidence_type: str
    evidence_subtype: str | None = None
    filename: str
    file_size: int | None = None
    mime_type: str | None = None
    sha256_hash: str
    storage_ref: str
    extraction_confidence: Decimal | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DecisionCaseSummary(BaseModel):
    id: UUID
    organization_id: UUID
    status: str
    criticality: str
    intake_list_id: UUID | None = None
    primary_rfq_id: UUID | None = None
    area_solicitante: str | None = None
    objeto_resumen: str | None = None
    frozen_first_at: datetime | None = None
    created_at: datetime
    evidence_count: int = 0
    event_count: int = 0

    model_config = {"from_attributes": True}


class DecisionCaseDetail(BaseModel):
    case: DecisionCaseSummary
    timeline: list[CaseTimelineEventOut]
    evidences: list[CaseEvidenceOut]
    fulfillment: "FulfillmentOut | None" = None
    chain_intact: bool


class ChainIntegrityResult(BaseModel):
    intact: bool
    total_events: int
    broken_at: UUID | None = None


class GapOut(BaseModel):
    gap_type: str
    severity: str
    description: str
    event_id: UUID | None = None


class EvidencePackOut(BaseModel):
    case_id: UUID
    organization_id: UUID
    status: str
    timeline: list[CaseTimelineEventOut]
    evidences: list[CaseEvidenceOut]
    fulfillment: "FulfillmentOut | None" = None
    integrity: ChainIntegrityResult
    pack_signature: str


class PublicVerifyOut(BaseModel):
    case_id: UUID
    integrity_status: str  # VERIFIED | TAMPERED
    chain_anchor: str
    verified_at: datetime


# Import fulfillment for forward ref
from app.schemas.fulfillment import FulfillmentOut  # noqa: E402

DecisionCaseDetail.model_rebuild()
EvidencePackOut.model_rebuild()
