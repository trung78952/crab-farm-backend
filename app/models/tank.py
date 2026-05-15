import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tank(Base):
    __tablename__ = "tanks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="RESTRICT"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    row_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    col_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    level_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    x_position: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    y_position: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    z_position: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="empty", index=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    shelf = relationship("Shelf", back_populates="tanks")
    images = relationship("Image", back_populates="tank", passive_deletes=True)
    detections = relationship("Detection", back_populates="tank", passive_deletes=True)
    motion_commands = relationship("MotionCommand", back_populates="tank", passive_deletes=True)
    harvests = relationship("Harvest", back_populates="tank", passive_deletes=True)
    scan_job_items = relationship("ScanJobItem", back_populates="tank", passive_deletes=True)
    recheck_tasks = relationship("RecheckTask", back_populates="tank", passive_deletes=True)
    sensors = relationship("Sensor", back_populates="tank", passive_deletes=True)
    sensor_readings = relationship("SensorReading", back_populates="tank", passive_deletes=True)
    sensor_alert_rules = relationship("SensorAlertRule", back_populates="tank", passive_deletes=True)
    sensor_alerts = relationship("SensorAlert", back_populates="tank", passive_deletes=True)
