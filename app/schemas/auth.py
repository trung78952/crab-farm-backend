from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRole(str, Enum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    id: UUID
    username: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class CreateAdminRequest(BaseModel):
    username: str = "admin"
    password: str = "admin123"
    email: EmailStr | None = "admin@example.com"
