import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Boolean, Numeric, Date, DateTime, ForeignKey,
    Index, CheckConstraint, Computed,
)
from app.db_types import UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    freight_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    payment_condition: Mapped[str | None] = mapped_column(String(255))
    delivery_time_days: Mapped[int | None] = mapped_column(Integer)
    valid_until: Mapped[date | None] = mapped_column(Date)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    rfq = relationship("RFQ", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_quote_status"),
        Index("idx_quotes_org", "organization_id"),
        Index("idx_quotes_rfq", "rfq_id"),
        Index("idx_quotes_supplier", "supplier_id"),
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    rfq_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfq_items.id")
    )
    description: Mapped[str | None] = mapped_column(String(500))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    unit: Mapped[str | None] = mapped_column(String(50))
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        Computed("unit_price * COALESCE(quantity, 1)", persisted=True),
    )
    match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    extracted_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    quote = relationship("Quote", back_populates="items")

    __table_args__ = (
        CheckConstraint("match_confidence BETWEEN 0 AND 1", name="ck_qi_match_conf"),
        Index("idx_quote_items_quote", "quote_id"),
    )
