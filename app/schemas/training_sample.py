from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DatasetSplit(str, Enum):
    train = "train"
    val = "val"
    test = "test"


class TrainingSampleLabelRequest(BaseModel):
    human_label: str
    bbox: dict[str, Any] | None = None
    dataset_split: DatasetSplit | None = None
    note: str | None = None


class TrainingSampleRead(BaseModel):
    id: UUID
    image_id: UUID
    detection_id: UUID | None
    tank_id: UUID
    ai_label: str | None
    human_label: str | None
    bbox: dict[str, Any] | None
    is_verified: bool
    dataset_split: DatasetSplit | None
    note: str | None
    created_at: datetime
    verified_at: datetime | None
    verified_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


class DatasetExportRead(BaseModel):
    export_dir: str
    samples_exported: int
    note: str
