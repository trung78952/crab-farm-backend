import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SensorType(Base):
    __tablename__ = "sensor_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sensors = relationship("Sensor", back_populates="sensor_type")
    alert_rules = relationship("SensorAlertRule", back_populates="sensor_type")


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        CheckConstraint("tank_id IS NOT NULL OR shelf_id IS NOT NULL", name="has_owner"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensor_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensor_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    tank_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=True, index=True)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"), nullable=True, index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sensor_type = relationship("SensorType", back_populates="sensors")
    tank = relationship("Tank", back_populates="sensors")
    shelf = relationship("Shelf", back_populates="sensors")
    device = relationship("Device", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor", passive_deletes=True)
    alerts = relationship("SensorAlert", back_populates="sensor", passive_deletes=True)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    tank_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=True, index=True)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"), nullable=True, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sensor = relationship("Sensor", back_populates="readings")
    tank = relationship("Tank", back_populates="sensor_readings")
    shelf = relationship("Shelf", back_populates="sensor_readings")
    alerts = relationship("SensorAlert", back_populates="reading")


class SensorAlertRule(Base):
    __tablename__ = "sensor_alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensor_types.id", ondelete="CASCADE"), nullable=False, index=True)
    tank_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=True, index=True)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"), nullable=True, index=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sensor_type = relationship("SensorType", back_populates="alert_rules")
    tank = relationship("Tank", back_populates="sensor_alert_rules")
    shelf = relationship("Shelf", back_populates="sensor_alert_rules")


class SensorAlert(Base):
    __tablename__ = "sensor_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sensor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True)
    reading_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sensor_readings.id", ondelete="SET NULL"), nullable=True, index=True)
    tank_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=True, index=True)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shelves.id", ondelete="CASCADE"), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sensor = relationship("Sensor", back_populates="alerts")
    reading = relationship("SensorReading", back_populates="alerts")
    tank = relationship("Tank", back_populates="sensor_alerts")
    shelf = relationship("Shelf", back_populates="sensor_alerts")
