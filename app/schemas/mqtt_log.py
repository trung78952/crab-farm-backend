from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MqttLogRead(BaseModel):
    id: UUID
    direction: str
    topic: str
    payload: dict[str, Any]
    qos: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
