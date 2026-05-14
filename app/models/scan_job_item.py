import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScanJobItem(Base):
    __tablename__ = "scan_job_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    tank_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    motion_command_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("motion_commands.id", ondelete="SET NULL"), nullable=True)
    camera_command_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("images.id", ondelete="SET NULL"), nullable=True)
    detection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    scan_job = relationship("ScanJob", back_populates="items")
    tank = relationship("Tank", back_populates="scan_job_items")
    image = relationship("Image", back_populates="scan_job_items")
    detection = relationship("Detection", back_populates="scan_job_items")
    motion_command = relationship("MotionCommand")
