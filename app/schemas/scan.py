from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.core.timezone import to_app_timezone


class ScanMode(str, Enum):
    all_tanks = "all_tanks"
    selected_tanks = "selected_tanks"
    single_tank = "single_tank"


class ScanScheduleMode(str, Enum):
    all_tanks = "all_tanks"
    selected_tanks = "selected_tanks"
    single_shelf = "single_shelf"


class ScanJobStatus(str, Enum):
    queued = "queued"
    running = "running"
    success = "success"
    partial_success = "partial_success"
    failed = "failed"
    cancelled = "cancelled"
    simulated = "simulated"
    waiting_for_hardware = "waiting_for_hardware"


class ScanJobItemStatus(str, Enum):
    queued = "queued"
    waiting_for_motion = "waiting_for_motion"
    moving = "moving"
    motion_done = "motion_done"
    waiting_for_camera = "waiting_for_camera"
    capturing = "capturing"
    image_received = "image_received"
    detecting = "detecting"
    success = "success"
    failed = "failed"
    timeout = "timeout"
    simulated = "simulated"


class ScanScheduleBase(BaseModel):
    shelf_id: UUID | None = None
    name: str
    interval_minutes: int = Field(gt=0)
    is_active: bool = True
    scan_mode: ScanScheduleMode = ScanScheduleMode.all_tanks
    tank_ids: list[UUID] | None = None
    priority: int = Field(default=100, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    next_run_at: datetime | None = None

    @model_validator(mode="after")
    def validate_selected_tanks(self):
        if self.scan_mode == ScanScheduleMode.selected_tanks and not self.tank_ids:
            raise ValueError("tank_ids is required when scan_mode is selected_tanks")
        if self.scan_mode == ScanScheduleMode.single_shelf and self.shelf_id is None:
            raise ValueError("shelf_id is required when scan_mode is single_shelf")
        return self


class ScanScheduleCreate(ScanScheduleBase):
    pass


class ScanScheduleUpdate(BaseModel):
    shelf_id: UUID | None = None
    name: str | None = None
    interval_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    scan_mode: ScanScheduleMode | None = None
    tank_ids: list[UUID] | None = None
    priority: int | None = Field(default=None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    next_run_at: datetime | None = None


class ScanScheduleRead(BaseModel):
    id: UUID
    shelf_id: UUID | None
    name: str
    interval_minutes: int
    is_active: bool
    scan_mode: ScanScheduleMode
    tank_ids: list[UUID] | None
    priority: int
    start_time: datetime | None
    end_time: datetime | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "start_time",
        "end_time",
        "last_run_at",
        "next_run_at",
        "created_at",
        "updated_at",
        when_used="json",
    )
    def serialize_datetime(self, value: datetime | None) -> datetime | None:
        return to_app_timezone(value)

    model_config = ConfigDict(from_attributes=True)


class ScanJobItemRead(BaseModel):
    id: UUID
    scan_job_id: UUID
    tank_id: UUID
    status: ScanJobItemStatus
    motion_command_id: UUID | None = None
    camera_command_id: str | None = None
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
    shelf_id: UUID | None = None
    job_type: str = "manual_scan"
    status: ScanJobStatus
    priority: int = 100
    scan_mode: ScanMode
    total_tanks: int
    completed_tanks: int
    failed_tanks: int = 0
    is_simulation: bool = False
    error_message: str | None = None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[ScanJobItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
