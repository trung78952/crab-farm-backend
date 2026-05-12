import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Harvest(Base):
    __tablename__ = "harvests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tank_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tanks.id", ondelete="CASCADE"), nullable=False, index=True)
    detection_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    motion_command_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("motion_commands.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tank = relationship("Tank", back_populates="harvests")
    detection = relationship("Detection", back_populates="harvests")
    motion_command = relationship("MotionCommand", back_populates="harvests")
