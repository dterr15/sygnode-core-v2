from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class QuoteItemInput(BaseModel):
    rfq_item_id: UUID | None = None
    description: str | None = None
    unit_price: Decimal
    quantity: Decimal | None = None
    unit: str | None = None
    match_confidence: float | None = None
    extracted_by_ai: bool = False


class QuoteItemOut(BaseModel):
    id: UUID
    quote_id: UUID
    rfq_item_id: UUID | None = None
    description: str | None = None
    unit_price: Decimal
    quantity: Decimal | None = None
    unit: str | None = None
    subtotal: Decimal | None = None
    match_confidence: Decimal | None = None
    extracted_by_ai: bool

    model_config = {"from_attributes": True}


class QuoteCreate(BaseModel):
    supplier_id: UUID
    total_amount: Decimal
    currency: str = "CLP"
    freight_total: Decimal = Decimal("0")
    payment_condition: str | None = None
    delivery_time_days: int | None = None
    valid_until: date | None = None
    items: list[QuoteItemInput] = Field(default_factory=list)


class QuoteOut(BaseModel):
    id: UUID
    organization_id: UUID
    rfq_id: UUID
    supplier_id: UUID
    status: str
    total_amount: Decimal
    freight_total: Decimal
    currency: str
    payment_condition: str | None = None
    delivery_time_days: int | None = None
    valid_until: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
