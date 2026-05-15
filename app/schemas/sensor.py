from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SensorStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    error = "error"
    maintenance = "maintenance"


class SensorAlertType(str, Enum):
    low = "low"
    high = "high"
    error = "error"


class SensorAlertStatus(str, Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"


class SensorTypeBase(BaseModel):
    code: str
    name: str
    unit: str
    min_value: float | None = None
    max_value: float | None = None
    metadata: dict[str, Any] | None = None


class SensorTypeCreate(SensorTypeBase):
    pass


class SensorTypeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    metadata: dict[str, Any] | None = None


class SensorTypeRead(SensorTypeBase):
    id: UUID
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SensorBase(BaseModel):
    code: str
    name: str
    sensor_type_id: UUID
    tank_id: UUID | None = None
    shelf_id: UUID | None = None
    device_id: UUID | None = None
    status: SensorStatus = SensorStatus.active
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_owner(self):
        if self.tank_id is None and self.shelf_id is None:
            raise ValueError("At least one of tank_id or shelf_id is required")
        return self


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    sensor_type_id: UUID | None = None
    tank_id: UUID | None = None
    shelf_id: UUID | None = None
    device_id: UUID | None = None
    status: SensorStatus | None = None
    metadata: dict[str, Any] | None = None


class SensorRead(SensorBase):
    id: UUID
    metadata: dict[str, Any] | None = Field(default=None, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SensorReadingCreate(BaseModel):
    sensor_id: UUID
    tank_id: UUID | None = None
    shelf_id: UUID | None = None
    value: float
    unit: str | None = None
    measured_at: datetime | None = None


class SensorReadingRead(BaseModel):
    id: UUID
    sensor_id: UUID
    tank_id: UUID | None
    shelf_id: UUID | None
    value: float
    unit: str
    measured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorAlertRuleBase(BaseModel):
    sensor_type_id: UUID
    tank_id: UUID | None = None
    shelf_id: UUID | None = None
    min_value: float | None = None
    max_value: float | None = None
    is_active: bool = True


class SensorAlertRuleCreate(SensorAlertRuleBase):
    pass


class SensorAlertRuleUpdate(BaseModel):
    sensor_type_id: UUID | None = None
    tank_id: UUID | None = None
    shelf_id: UUID | None = None
    min_value: float | None = None
    max_value: float | None = None
    is_active: bool | None = None


class SensorAlertRuleRead(SensorAlertRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SensorAlertRead(BaseModel):
    id: UUID
    sensor_id: UUID
    reading_id: UUID | None
    tank_id: UUID | None
    shelf_id: UUID | None
    alert_type: SensorAlertType
    message: str
    status: SensorAlertStatus
    created_at: datetime
    resolved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
