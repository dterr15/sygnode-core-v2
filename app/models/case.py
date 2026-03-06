import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Boolean, Numeric, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, Index, CheckConstraint,
)
from app.db_types import UUIDType as UUID, JSONType as JSONB, ArrayType as ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DecisionCase(Base):
    __tablename__ = "decision_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    intake_list_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("intake_lists.id")
    )
    primary_rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    area_solicitante: Mapped[str | None] = mapped_column(String(255))
    objeto_resumen: Mapped[str | None] = mapped_column(Text)
    contexto: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(), nullable=False, default=list)
    frozen_first_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    timeline_events = relationship("CaseTimelineEvent", back_populates="case", lazy="selectin")
    evidences = relationship("CaseEvidence", back_populates="case", lazy="selectin")
    versions = relationship("CaseVersion", back_populates="case", lazy="selectin")
    fulfillment = relationship("CaseFulfillment", back_populates="case", uselist=False, lazy="selectin")

    __table_args__ = (
        CheckConstraint("status IN ('OPEN','FROZEN','ARCHIVED')", name="ck_case_status"),
        CheckConstraint("criticality IN ('NORMAL','HIGH','CRITICAL')", name="ck_case_criticality"),
        Index("idx_cases_org", "organization_id"),
        Index("idx_cases_status", "organization_id", "status"),
        Index("idx_cases_intake", "intake_list_id"),
    )


class CaseTimelineEvent(Base):
    """
    APPEND-ONLY. No UPDATE, no DELETE — enforced by PostgreSQL RULEs.
    G1: Trazabilidad Inviolable.
    """
    __tablename__ = "case_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_role: Mapped[str | None] = mapped_column(String(50))
    event_metadata: Mapped[dict | None] = mapped_column(JSONB)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    prev_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    artifact_hash: Mapped[str | None] = mapped_column(String(64))
    related_doc_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(), nullable=False, default=list
    )

    case = relationship("DecisionCase", back_populates="timeline_events")

    __table_args__ = (
        CheckConstraint(
            "event_type IN ("
            "'CASE_CREATED','EVIDENCE_UPLOADED','COMPARATIVE_GENERATED',"
            "'GAP_FLAGGED','PO_INGESTED','AWARD_INFERRED',"
            "'NEGOTIATION_FLAGGED','UPLIFT_FLAGGED','WITHIN_RANGE')",
            name="ck_timeline_event_type",
        ),
        Index("idx_timeline_case", "case_id", "event_timestamp"),
        Index("idx_timeline_hash", "event_hash"),
        Index("idx_timeline_prev", "prev_event_hash"),
    )


class CaseEvidence(Base):
    __tablename__ = "case_evidences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=True
    )
    evidence_type: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_subtype: Mapped[str | None] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    source_table: Mapped[str | None] = mapped_column(String(100))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    extracted_data: Mapped[dict | None] = mapped_column(JSONB)
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    case = relationship("DecisionCase", back_populates="evidences")

    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('REQUIREMENT','QUOTE','PO','OTHER')",
            name="ck_evidence_type",
        ),
        Index("idx_evidences_case", "case_id"),
    )


class CaseVersion(Base):
    __tablename__ = "case_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    decision_data: Mapped[dict | None] = mapped_column(JSONB)
    integrity_hash: Mapped[str | None] = mapped_column(String(64))
    frozen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    frozen_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    frozen_by_role: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[str | None] = mapped_column(String(50))
    validation_details: Mapped[dict | None] = mapped_column(JSONB)

    case = relationship("DecisionCase", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("case_id", "version_number", name="uq_case_version"),
    )


class CaseFulfillment(Base):
    __tablename__ = "case_fulfillment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_cases.id"), nullable=False
    )
    po_number: Mapped[str] = mapped_column(String(100), nullable=False)
    po_date: Mapped[date | None] = mapped_column(Date)
    po_issue_date_confidence: Mapped[str | None] = mapped_column(String(20))
    final_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id")
    )
    supplier_identification_confidence: Mapped[str | None] = mapped_column(String(20))
    approved_by_name: Mapped[str | None] = mapped_column(String(255))
    approved_by_role: Mapped[str | None] = mapped_column(String(100))
    delta_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    delta_abs: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    baseline_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    variance_flags: Mapped[list[str]] = mapped_column(ARRAY(), nullable=False, default=list)
    variance_justification: Mapped[str | None] = mapped_column(Text)
    requires_justification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reconciliation_status: Mapped[str] = mapped_column(String(25), nullable=False, default="PENDING")
    award_type: Mapped[str | None] = mapped_column(String(20))
    award_confidence: Mapped[str | None] = mapped_column(String(20))
    award_inferred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    po_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("case_evidences.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    case = relationship("DecisionCase", back_populates="fulfillment")

    __table_args__ = (
        CheckConstraint(
            "reconciliation_status IN ('PENDING','MATCH','VARIANCE_JUSTIFIED')",
            name="ck_fulfillment_recon_status",
        ),
        CheckConstraint(
            "award_type IS NULL OR award_type IN ('total','fraccionada','directa')",
            name="ck_fulfillment_award_type",
        ),
        Index("idx_fulfillment_case", "case_id"),
    )
