import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tank_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    class_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="none", index=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tank = relationship("Tank", back_populates="detections")
    image = relationship("Image", back_populates="detections")
    harvests = relationship("Harvest", back_populates="detection")
    scan_job_items = relationship("ScanJobItem", back_populates="detection")
