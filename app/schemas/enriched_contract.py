"""
JSON Contract validation — doc 04.
Every Gemini response is validated against these schemas before persisting (R4).
"""

from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator


class QuoteExtractionItem(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal = Field(..., ge=0)
    subtotal: Decimal | None = None
    match_rfq_item_id: str | None = None
    match_confidence: float = Field(0, ge=0, le=1)


class QuoteExtraction(BaseModel):
    supplier_name: str
    supplier_rut: str | None = None
    po_number: str | None = None
    quote_date: str | None = None
    valid_until: str | None = None
    payment_condition: str | None = None
    delivery_time_days: int | None = None
    currency: str = Field(..., pattern="^(CLP|USD|EUR|UF)$")
    total_amount: Decimal = Field(..., ge=0)
    freight_total: Decimal = Field(default=0, ge=0)
    items: list[QuoteExtractionItem]


class AnalysisDistribution(BaseModel):
    supplier_id: str | None = None
    supplier_name: str | None = None
    items_awarded: list[str] = Field(default_factory=list)
    amount_awarded: Decimal | None = None
    rationale: str | None = None


class AnalysisItemDetail(BaseModel):
    item_description: str
    best_supplier: str | None = None
    best_price: Decimal | None = None
    price_spread_pct: float | None = None
    recommendation: str | None = None


class AnalysisData(BaseModel):
    recommendation: str
    strategy: str = Field(..., pattern="^(BTC|CONSOLIDACION|HIBRIDA)$")
    distribution: list[AnalysisDistribution] = Field(default_factory=list)
    item_analysis: list[AnalysisItemDetail] = Field(default_factory=list)


class ExtractionMetadata(BaseModel):
    extraction_confidence: float = Field(..., ge=0, le=1)
    model_used: str
    processed_at: datetime
    warnings: list[str] = Field(default_factory=list)


class SygnodeEnrichedContract(BaseModel):
    """Top-level schema — validates complete Gemini response."""
    quote_extraction: QuoteExtraction
    analysis: AnalysisData
    metadata: ExtractionMetadata


class POExtraction(BaseModel):
    """Schema for PO data extraction."""
    po_number: str
    po_date: str | None = None
    po_issue_date_confidence: str = "unknown"
    supplier_name: str | None = None
    supplier_identification_confidence: str = "unknown"
    total_amount: Decimal = Field(..., ge=0)
    currency: str = Field(..., pattern="^(CLP|USD|EUR|UF)$")
    approved_by_name: str | None = None
    approved_by_role: str | None = None
    items: list[dict] = Field(default_factory=list)


def validate_quote_extraction(raw_json: dict) -> QuoteExtraction:
    """Validate Gemini quote extraction against schema. Raises ValueError on failure."""
    return QuoteExtraction.model_validate(raw_json)


def validate_analysis(raw_json: dict) -> AnalysisData:
    """Validate Gemini analysis against schema. Raises ValueError on failure."""
    return AnalysisData.model_validate(raw_json)


def validate_po_extraction(raw_json: dict) -> POExtraction:
    """Validate Gemini PO extraction against schema. Raises ValueError on failure."""
    return POExtraction.model_validate(raw_json)
