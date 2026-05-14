import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scan_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="SET NULL"), nullable=True, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_scan", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    scan_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    total_tanks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_tanks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_tanks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_simulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
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

    schedule = relationship("ScanSchedule", back_populates="scan_jobs")
    shelf = relationship("Shelf", back_populates="scan_jobs")
    items = relationship("ScanJobItem", back_populates="scan_job", cascade="all, delete-orphan")
