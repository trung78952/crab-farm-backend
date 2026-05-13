from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScanMode(str, Enum):
    all_tanks = "all_tanks"
    selected_tanks = "selected_tanks"
    single_tank = "single_tank"


class ScanScheduleMode(str, Enum):
    all_tanks = "all_tanks"
    selected_tanks = "selected_tanks"


class ScanJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"
    cancelled = "cancelled"


class ScanJobItemStatus(str, Enum):
    queued = "queued"
    moving = "moving"
    capturing = "capturing"
    detecting = "detecting"
    success = "success"
    failed = "failed"


class ScanScheduleBase(BaseModel):
    name: str
    interval_minutes: int = Field(gt=0)
    is_active: bool = True
    scan_mode: ScanScheduleMode = ScanScheduleMode.all_tanks
    tank_ids: list[UUID] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    next_run_at: datetime | None = None

    @model_validator(mode="after")
    def validate_selected_tanks(self):
        if self.scan_mode == ScanScheduleMode.selected_tanks and not self.tank_ids:
            raise ValueError("tank_ids is required when scan_mode is selected_tanks")
        return self


class ScanScheduleCreate(ScanScheduleBase):
    pass


class ScanScheduleUpdate(BaseModel):
    name: str | None = None
    interval_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    scan_mode: ScanScheduleMode | None = None
    tank_ids: list[UUID] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    next_run_at: datetime | None = None


class ScanScheduleRead(BaseModel):
    id: UUID
    name: str
    interval_minutes: int
    is_active: bool
    scan_mode: ScanScheduleMode
    tank_ids: list[UUID] | None
    start_time: datetime | None
    end_time: datetime | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanJobItemRead(BaseModel):
    id: UUID
    scan_job_id: UUID
    tank_id: UUID
    status: ScanJobItemStatus
    image_id: UUID | None
    detection_id: UUID | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScanJobRead(BaseModel):
    id: UUID
    schedule_id: UUID | None
    status: ScanJobStatus
    scan_mode: ScanMode
    total_tanks: int
    completed_tanks: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[ScanJobItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
