from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class JustifyVarianceRequest(BaseModel):
    justification: str = Field(..., min_length=50)


class FulfillmentOut(BaseModel):
    id: UUID
    case_id: UUID
    po_number: str
    po_date: date | None = None
    po_issue_date_confidence: str | None = None
    final_amount: Decimal
    currency: str
    supplier_name: str | None = None
    supplier_id: UUID | None = None
    supplier_identification_confidence: str | None = None
    delta_pct: Decimal | None = None
    delta_abs: Decimal | None = None
    baseline_amount: Decimal | None = None
    variance_flags: list[str] = []
    variance_justification: str | None = None
    requires_justification: bool
    reconciliation_status: str
    award_type: str | None = None
    award_confidence: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class POUploadResponse(BaseModel):
    fulfillment_id: UUID
    po_data: dict
    award: dict
    contrast: dict


class ContrastResult(BaseModel):
    delta_pct: Decimal
    delta_abs: Decimal
    baseline_amount: Decimal
    flag: str  # WITHIN_RANGE, UPLIFT_FLAGGED, NEGOTIATION_FLAGGED
    requires_justification: bool
