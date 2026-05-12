from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HarvestStatus(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class HarvestQueueRequest(BaseModel):
    note: str | None = None


class HarvestRead(BaseModel):
    id: UUID
    tank_id: UUID
    detection_id: UUID | None
    motion_command_id: UUID | None
    status: HarvestStatus
    note: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
