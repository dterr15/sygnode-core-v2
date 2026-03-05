from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=255)
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    region: str | None = None
    categories: list[str] = Field(default_factory=list)
    rut: str | None = None
    lat: float | None = None
    lng: float | None = None
    service_radius_km: int | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    region: str | None = None
    categories: list[str] | None = None
    rut: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_validated: bool | None = None


class SupplierOut(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    rut: str | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    region: str | None = None
    country: str
    categories: list[str]
    tags: list[str]
    rating: Decimal | None = None
    total_quotes: int
    awarded_quotes: int
    lat: Decimal | None = None
    lng: Decimal | None = None
    is_validated: bool
    source: str
    confidence_score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SupplierScore(BaseModel):
    supplier_id: UUID
    supplier_name: str
    score_final: float
    is_validated: bool
    score_breakdown: dict | None = None
