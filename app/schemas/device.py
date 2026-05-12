from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeviceType(str, Enum):
    esp32_motion = "esp32_motion"
    pi_camera = "pi_camera"
    server = "server"


class DeviceStatus(str, Enum):
    online = "online"
    offline = "offline"
    error = "error"


class DeviceBase(BaseModel):
    code: str
    type: DeviceType
    name: str
    mqtt_client_id: str | None = None
    status: DeviceStatus = DeviceStatus.offline
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    pass


class DeviceStatusUpdate(BaseModel):
    status: DeviceStatus
    last_seen_at: datetime | None = None


class DeviceRead(DeviceBase):
    id: UUID
    last_seen_at: datetime | None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
