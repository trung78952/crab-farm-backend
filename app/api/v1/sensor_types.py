from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.sensor import SensorTypeCreate, SensorTypeRead, SensorTypeUpdate
from app.services import sensor_service

router = APIRouter()


@router.get("", response_model=list[SensorTypeRead])
async def list_sensor_types(db: AsyncSession = Depends(get_db)):
    return await sensor_service.list_sensor_types(db)


@router.post("", response_model=SensorTypeRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def create_sensor_type(data: SensorTypeCreate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.create_sensor_type(db, data)


@router.patch("/{sensor_type_id}", response_model=SensorTypeRead, dependencies=[Depends(require_roles("operator"))])
async def update_sensor_type(sensor_type_id: UUID, data: SensorTypeUpdate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.update_sensor_type(db, sensor_type_id, data)
