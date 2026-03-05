import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Boolean, Numeric, Text, DateTime, ForeignKey,
    Index, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IntakeList(Base):
    __tablename__ = "intake_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDIENTE_REVISION")
    validation_status: Mapped[str | None] = mapped_column(
        String(40), default="STAGED_PENDING_VALIDATION"
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500))
    message_id_header: Mapped[str | None] = mapped_column(String(500))
    paste_hash: Mapped[str | None] = mapped_column(String(64))
    from_email: Mapped[str | None] = mapped_column(String(255))
    from_name: Mapped[str | None] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(500))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    context_body: Mapped[str | None] = mapped_column(Text)
    raw_email_storage_ref: Mapped[str | None] = mapped_column(String(500))
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"))
    validated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = relationship("IntakeItem", back_populates="intake_list", lazy="selectin", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDIENTE_REVISION','EN_COTIZACION','ARCHIVADA','CERRADA')",
            name="ck_intake_status",
        ),
        CheckConstraint(
            "validation_status IN ('STAGED_PENDING_VALIDATION','APPROVED_GENERATED','REJECTED_MIN_DATA_PENDING')",
            name="ck_intake_validation_status",
        ),
        CheckConstraint(
            "source IN ('email','whatsapp_paste','manual','api')",
            name="ck_intake_source",
        ),
        Index("idx_intake_org", "organization_id"),
        Index("idx_intake_status", "organization_id", "status"),
        Index("idx_intake_validation", "validation_status"),
        # Partial unique: emails are idempotent
        Index(
            "idx_intake_email_idempotent",
            "source", "source_ref",
            unique=True,
            postgresql_where="source = 'email' AND source_ref IS NOT NULL",
        ),
    )


class IntakeItem(Base):
    __tablename__ = "intake_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_lists.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    uom: Mapped[str] = mapped_column(String(50), nullable=False, default="un")
    is_placeholder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    original_text: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    intake_list = relationship("IntakeList", back_populates="items")

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_ii_confidence"),
        Index("idx_intake_items_list", "list_id"),
    )
