import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Boolean, Numeric, DateTime, ForeignKey,
    UniqueConstraint, Index, CheckConstraint,
)
from app.db_types import UUIDType as UUID, ArrayType as ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rut: Mapped[str | None] = mapped_column(String(12))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="CL")
    categories: Mapped[list[str]] = mapped_column(ARRAY(), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(), nullable=False, default=list)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    total_quotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    awarded_quotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    service_radius_km: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    validation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    needs_attention: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_activity_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_supplier_rating"),
        CheckConstraint("confidence_score BETWEEN 0 AND 100", name="ck_supplier_confidence"),
        CheckConstraint("source IN ('manual','ia_inferred')", name="ck_supplier_source"),
        Index("idx_suppliers_org", "organization_id"),
        Index("idx_suppliers_validated", "organization_id", "is_validated"),
    )


class SupplierItemIndex(Base):
    __tablename__ = "supplier_item_index"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    item_normalized: Mapped[str] = mapped_column(String(500), nullable=False)
    item_category: Mapped[str | None] = mapped_column(String(100))
    times_quoted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    times_selected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selection_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))
    last_quote_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_quote_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avg_ranking_position: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ia_inferred")
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback_adjustment: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    explicit_feedback_adjustment: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    __table_args__ = (
        UniqueConstraint("supplier_id", "item_normalized", name="uq_sii_supplier_item"),
        Index("idx_sii_supplier", "supplier_id"),
        Index("idx_sii_category", "item_category"),
    )


class SupplierCategories(Base):
    __tablename__ = "supplier_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100))
    num_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_quotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selection_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ia_inferred")
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("idx_sc_supplier", "supplier_id"),
    )
