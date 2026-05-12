from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DetectionAction(str, Enum):
    none = "none"
    recheck = "recheck"
    harvest = "harvest"
    alert = "alert"


class DetectionMockCreate(BaseModel):
    tank_id: UUID
    image_id: UUID
    class_name: str
    confidence: float = Field(ge=0, le=1)
    bbox: dict[str, Any]
    action: DetectionAction | None = None
    model_name: str | None = "mock-detector"


class DetectionRead(BaseModel):
    id: UUID
    tank_id: UUID
    image_id: UUID
    class_name: str
    confidence: float
    bbox: dict[str, Any]
    action: DetectionAction
    model_name: str | None
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
