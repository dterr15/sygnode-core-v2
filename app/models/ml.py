import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Integer, Boolean, Numeric, DateTime, ForeignKey, Index
from app.db_types import UUIDType as UUID, JSONType as JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    accuracy: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    precision_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    recall: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    f1_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    samples_trained: Mapped[int | None] = mapped_column(Integer)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("idx_ml_active", "is_active", postgresql_where="is_active = TRUE"),
    )
