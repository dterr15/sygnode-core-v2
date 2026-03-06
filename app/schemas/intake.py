from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class IntakePasteRequest(BaseModel):
    text: str = Field(..., min_length=3)
    source: str = "whatsapp_paste"
    client_id: UUID | None = None


class IntakeItemUpdate(BaseModel):
    description: str | None = None
    quantity: Decimal | None = None
    uom: str | None = None
    is_confirmed: bool | None = None


class IntakeTransitionRequest(BaseModel):
    to_status: str
    reason: str | None = None


class IntakeApproveRequest(BaseModel):
    notes: str | None = None


class IntakeApproveResponse(BaseModel):
    success: bool
    case_id: UUID
    rfq_id: UUID


class IntakeRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class IntakeItemOut(BaseModel):
    id: UUID
    list_id: UUID
    description: str
    quantity: Decimal | None = None
    uom: str
    is_placeholder: bool
    needs_review: bool
    needs_clarification: bool
    is_confirmed: bool
    confidence_score: Decimal | None = None
    original_text: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class IntakeListOut(BaseModel):
    id: UUID
    organization_id: UUID
    status: str
    validation_status: str | None = None
    title: str
    source: str
    source_ref: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    subject: str | None = None
    received_at: datetime | None = None
    client_id: UUID | None = None
    validated_by_user_id: UUID | None = None
    validated_at: datetime | None = None
    rejected_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IntakeDetailOut(BaseModel):
    list: IntakeListOut
    items: list[IntakeItemOut]
