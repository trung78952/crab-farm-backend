from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AiStatusRead(BaseModel):
    enabled: bool
    mock_mode: bool
    simulation_mode: bool
    active_model_path: str
    active_model_version: str
    confidence_threshold: float
    image_size: int


class AiModelActivateRequest(BaseModel):
    model_path: str
    model_version: str
    name: str | None = None
    classes: list[str] | None = None


class AiModelRead(BaseModel):
    id: UUID
    name: str
    version: str
    model_path: str
    is_active: bool
    classes: list[str]
    metrics: dict[str, Any] | None
    created_at: datetime
    activated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
