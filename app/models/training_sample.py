import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TrainingSample(Base):
    __tablename__ = "training_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    detection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    tank_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_label: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    human_label: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    bbox: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    dataset_split: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    image = relationship("Image")
    detection = relationship("Detection")
    tank = relationship("Tank")
