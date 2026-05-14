from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, CreateAdminRequest, LoginRequest, TokenResponse


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    user.last_login_at = datetime.now(timezone.utc)
    token = create_access_token(str(user.id), {"username": user.username, "role": user.role})
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=token, user=user)


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    return await db.get(User, user_id)


async def create_admin_user(db: AsyncSession, data: CreateAdminRequest) -> User:
    result = await db.execute(select(User).where(User.username == data.username))
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.email = data.email
        existing.password_hash = hash_password(data.password)
        existing.role = "admin"
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(db: AsyncSession, user: User, data: ChangePasswordRequest) -> dict[str, str]:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "Password changed successfully"}
