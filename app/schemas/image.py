from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImageKind(str, Enum):
    raw = "raw"
    detected = "detected"
    verify = "verify"


class ImageCreate(BaseModel):
    tank_id: UUID
    device_id: UUID | None = None
    image_path: str
    image_url: str
    kind: ImageKind = ImageKind.raw
    captured_at: datetime | None = None


class ImageRead(BaseModel):
    id: UUID
    tank_id: UUID
    device_id: UUID | None
    image_path: str
    image_url: str
    kind: ImageKind
    captured_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CameraCaptureResponse(BaseModel):
    cmd_id: str
    topic: str
    payload: dict


class CameraUploadResponse(BaseModel):
    image_id: UUID
    image_url: str
