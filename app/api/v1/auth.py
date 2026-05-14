from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.schemas.auth import ChangePasswordRequest, CreateAdminRequest, LoginRequest, MessageResponse, TokenResponse, UserRead
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.authenticate_user(db, data)


@router.get("/me", response_model=UserRead)
async def me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    return {"status": "ok"}


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await auth_service.change_password(db, current_user, data)


@router.post("/create-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_admin(
    data: CreateAdminRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    return await auth_service.create_admin_user(db, data)
