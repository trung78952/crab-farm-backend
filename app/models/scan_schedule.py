import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScanSchedule(Base):
    __tablename__ = "scan_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user_periodic", index=True)
    tag: Mapped[str] = mapped_column(String(16), nullable=False, default="USER", index=True)
    scan_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="all_tanks", index=True)
    tank_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    run_once: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stop_condition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    auto_reason: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    parent_detection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    shelf = relationship("Shelf", back_populates="scan_schedules")
    scan_jobs = relationship("ScanJob", back_populates="schedule")
