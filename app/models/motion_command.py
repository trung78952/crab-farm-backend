import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MotionCommand(Base):
    __tablename__ = "motion_commands"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cmd_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    command_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tank_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tanks.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    mqtt_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    mqtt_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tank = relationship("Tank", back_populates="motion_commands")
    harvests = relationship("Harvest", back_populates="motion_command")
