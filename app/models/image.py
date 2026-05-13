import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tank_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="raw", index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tank = relationship("Tank", back_populates="images")
    device = relationship("Device", back_populates="images")
    detections = relationship("Detection", back_populates="image")
    scan_job_items = relationship("ScanJobItem", back_populates="image")
