from typing import Any

from pydantic import BaseModel, Field


class MqttPublishRequest(BaseModel):
    topic: str
    payload: dict[str, Any] | str
    qos: int = Field(default=0, ge=0, le=2)
    retain: bool = False
