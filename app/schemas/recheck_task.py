from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecheckReason(str, Enum):
    molting = "molting"
    suspected_soft_shell = "suspected_soft_shell"
    uncertain = "uncertain"
    bad_image = "bad_image"


class RecheckStatus(str, Enum):
    scheduled = "scheduled"
    queued = "queued"
    running = "running"
    done = "done"
    cancelled = "cancelled"
    failed = "failed"


class RecheckTaskCreate(BaseModel):
    tank_id: UUID
    source_detection_id: UUID | None = None
    reason: RecheckReason
    run_at: datetime
    priority: int = Field(default=10, ge=0)


class RecheckTaskRead(BaseModel):
    id: UUID
    tank_id: UUID
    source_detection_id: UUID | None
    reason: RecheckReason
    status: RecheckStatus
    run_at: datetime
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
