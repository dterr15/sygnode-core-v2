import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rut: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email_contact: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    industry: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="CL")
    subscription_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="trial"
    )
    subscription_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default="basic"
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    users = relationship("User", back_populates="organization", lazy="selectin")

    __table_args__ = (
        CheckConstraint(
            "subscription_status IN ('trial','active','cancelled','suspended')",
            name="ck_org_subscription_status",
        ),
        CheckConstraint(
            "subscription_tier IN ('basic','professional','enterprise')",
            name="ck_org_subscription_tier",
        ),
    )
