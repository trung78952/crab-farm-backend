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
    single_tank = "single_tank"
    single_shelf = "single_shelf"


class ScanScheduleType(str, Enum):
    user_periodic = "user_periodic"
    auto_recheck = "auto_recheck"
    auto_verify = "auto_verify"


class ScanScheduleTag(str, Enum):
    USER = "USER"
    AUTO = "AUTO"


class ScanAutoReason(str, Enum):
    molting = "molting"
    suspected_soft_shell = "suspected_soft_shell"
    uncertain = "uncertain"
    bad_image = "bad_image"


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
    skipped = "skipped"


class ScanScheduleBase(BaseModel):
    shelf_id: UUID | None = None
    name: str
    schedule_type: ScanScheduleType = ScanScheduleType.user_periodic
    tag: ScanScheduleTag = ScanScheduleTag.USER
    scan_mode: ScanScheduleMode = ScanScheduleMode.all_tanks
    tank_ids: list[UUID] | None = None
    interval_minutes: int | None = Field(default=None, gt=0)
    priority: int = Field(default=100, ge=0)
    is_active: bool = True
    run_once: bool = False
    max_runs: int | None = Field(default=None, gt=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    start_at: datetime | None = None
    next_run_at: datetime | None = None
    expires_at: datetime | None = None
    stop_condition: str | None = None
    created_by_system: bool = False
    auto_reason: ScanAutoReason | None = None
    parent_detection_id: UUID | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule_type == ScanScheduleType.user_periodic and not self.interval_minutes:
            raise ValueError("interval_minutes is required for user_periodic schedules")
        if self.schedule_type == ScanScheduleType.user_periodic:
            self.tag = ScanScheduleTag.USER
        elif self.tag == ScanScheduleTag.USER:
            self.tag = ScanScheduleTag.AUTO
        if self.scan_mode == ScanScheduleMode.selected_tanks and not self.tank_ids:
            raise ValueError("tank_ids is required when scan_mode is selected_tanks")
        if self.scan_mode == ScanScheduleMode.single_tank and len(self.tank_ids or []) != 1:
            raise ValueError("exactly one tank_id is required when scan_mode is single_tank")
        if self.scan_mode == ScanScheduleMode.single_shelf and self.shelf_id is None:
            raise ValueError("shelf_id is required when scan_mode is single_shelf")
        return self


class ScanScheduleCreate(ScanScheduleBase):
    run_immediately: bool = False


class ScanScheduleUpdate(BaseModel):
    shelf_id: UUID | None = None
    name: str | None = None
    schedule_type: ScanScheduleType | None = None
    tag: ScanScheduleTag | None = None
    scan_mode: ScanScheduleMode | None = None
    tank_ids: list[UUID] | None = None
    interval_minutes: int | None = Field(default=None, gt=0)
    priority: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    run_once: bool | None = None
    max_runs: int | None = Field(default=None, gt=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    start_at: datetime | None = None
    next_run_at: datetime | None = None
    expires_at: datetime | None = None
    stop_condition: str | None = None
    auto_reason: ScanAutoReason | None = None


class ScanScheduleRead(BaseModel):
    id: UUID
    shelf_id: UUID | None
    name: str
    schedule_type: ScanScheduleType = ScanScheduleType.user_periodic
    tag: ScanScheduleTag = ScanScheduleTag.USER
    scan_mode: ScanScheduleMode
    tank_ids: list[UUID] | None
    interval_minutes: int | None
    priority: int
    is_active: bool
    run_once: bool = False
    run_count: int = 0
    max_runs: int | None = None
    start_time: datetime | None
    end_time: datetime | None
    start_at: datetime | None = None
    last_run_at: datetime | None
    next_run_at: datetime | None
    expires_at: datetime | None = None
    stop_condition: str | None = None
    created_by_system: bool = False
    auto_reason: ScanAutoReason | None = None
    parent_detection_id: UUID | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer(
        "start_time",
        "end_time",
        "start_at",
        "last_run_at",
        "next_run_at",
        "expires_at",
        "completed_at",
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
