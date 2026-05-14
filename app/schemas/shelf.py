from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ShelfStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    maintenance = "maintenance"
    error = "error"


class ShelfBase(BaseModel):
    code: str
    name: str
    description: str | None = None
    motion_device_id: UUID | None = None
    camera_device_id: UUID | None = None
    status: ShelfStatus = ShelfStatus.active
    metadata: dict[str, Any] = Field(default_factory=dict)


class ShelfCreate(ShelfBase):
    pass


class ShelfUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    motion_device_id: UUID | None = None
    camera_device_id: UUID | None = None
    status: ShelfStatus | None = None
    metadata: dict[str, Any] | None = None


class ShelfRead(ShelfBase):
    id: UUID
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_", serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
