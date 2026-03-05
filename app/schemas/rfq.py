from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class RFQItemInput(BaseModel):
    description: str = Field(..., max_length=500)
    quantity: Decimal
    unit: str = Field(..., max_length=50)


class RFQItemOut(BaseModel):
    id: UUID
    rfq_id: UUID
    description: str
    quantity: Decimal
    unit: str
    sort_order: int

    model_config = {"from_attributes": True}


class RFQCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str | None = None
    items: list[RFQItemInput]
    client_id: UUID | None = None


class RFQUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    analysis_data: dict | None = None


class RFQOut(BaseModel):
    id: UUID
    organization_id: UUID
    reference_code: str
    title: str
    description: str | None = None
    status: str
    analysis_data: dict | None = None
    client_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RFQDetailOut(BaseModel):
    rfq: RFQOut
    items: list[RFQItemOut]
    quotes: list["QuoteOut"] = []
    email_status: list[dict] = []


# Forward ref resolved after QuoteOut is imported
from app.schemas.quote import QuoteOut  # noqa: E402

RFQDetailOut.model_rebuild()
