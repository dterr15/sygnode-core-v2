import uuid
from datetime import datetime, timezone, date

from sqlalchemy import String, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, Index
from app.db_types import UUIDType as UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    razon_social: Mapped[str] = mapped_column(String(255), nullable=False)
    rut: Mapped[str] = mapped_column(String(12), nullable=False)
    direccion_comercial: Mapped[str | None] = mapped_column(String(500))
    contrato_vigente: Mapped[str] = mapped_column(String(20), nullable=False, default="NO")
    contrato_fecha_inicio: Mapped[date | None] = mapped_column(Date)
    contrato_fecha_termino: Mapped[date | None] = mapped_column(Date)
    contacto_nombre: Mapped[str | None] = mapped_column(String(255))
    contacto_email: Mapped[str | None] = mapped_column(String(255))
    contacto_telefono: Mapped[str | None] = mapped_column(String(20))
    email_evidencias: Mapped[str | None] = mapped_column(String(255))
    telefono_consultas: Mapped[str | None] = mapped_column(String(20))
    domain_match: Mapped[str | None] = mapped_column(String(255))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("organization_id", "rut", name="uq_client_org_rut"),
        Index("idx_clients_org", "organization_id"),
    )
