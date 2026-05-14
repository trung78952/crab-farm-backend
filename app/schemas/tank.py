from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TankStatus(str, Enum):
    empty = "empty"
    normal = "normal"
    molting = "molting"
    soft_shell = "soft_shell"
    harvested = "harvested"
    error = "error"


class TankBase(BaseModel):
    shelf_id: UUID | None = None
    code: str
    name: str
    row_index: int = 0
    col_index: int = 0
    level_index: int = 0
    x_position: float = 0
    y_position: float = 0
    z_position: float = 0
    status: TankStatus = TankStatus.empty


class TankCreate(TankBase):
    pass


class TankUpdate(BaseModel):
    shelf_id: UUID | None = None
    code: str | None = None
    name: str | None = None
    row_index: int | None = None
    col_index: int | None = None
    level_index: int | None = None
    x_position: float | None = None
    y_position: float | None = None
    z_position: float | None = None
    status: TankStatus | None = None
    last_checked_at: datetime | None = None


class TankRead(TankBase):
    id: UUID
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
