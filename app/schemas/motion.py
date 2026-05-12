from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommandType(str, Enum):
    gcode = "gcode"
    move_to_tank = "move_to_tank"
    home = "home"
    harvest = "harvest"
    emergency_stop = "emergency_stop"


class MotionCommandStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    acknowledged = "acknowledged"
    done = "done"
    failed = "failed"
    timeout = "timeout"


class MoveToTankRequest(BaseModel):
    speed: int = 3000


class GCodeRequest(BaseModel):
    lines: list[str] = Field(min_length=1)


class MotionCommandRead(BaseModel):
    id: UUID
    cmd_id: str
    command_type: CommandType
    tank_id: UUID | None
    payload: dict[str, Any]
    status: MotionCommandStatus
    mqtt_topic: str
    mqtt_response: dict[str, Any] | None
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CommandCreatedResponse(BaseModel):
    cmd_id: str
    status: MotionCommandStatus
