from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.device import DeviceCreate, DeviceRead, DeviceStatusUpdate
from app.services import device_service

router = APIRouter()


@router.get("", response_model=list[DeviceRead])
async def list_devices(db: AsyncSession = Depends(get_db)):
    return await device_service.list_devices(db)


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin"))])
async def create_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)):
    return await device_service.create_device(db, data)


@router.patch("/{device_id}/status", response_model=DeviceRead, dependencies=[Depends(require_roles("admin", "operator"))])
async def update_device_status(device_id: UUID, data: DeviceStatusUpdate, db: AsyncSession = Depends(get_db)):
    return await device_service.update_device_status(db, device_id, data)
