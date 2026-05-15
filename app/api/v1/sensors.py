from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate
from app.services import sensor_service

router = APIRouter()


@router.get("", response_model=list[SensorRead])
async def list_sensors(
    shelf_id: UUID | None = None,
    tank_id: UUID | None = None,
    sensor_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await sensor_service.list_sensors(db, shelf_id=shelf_id, tank_id=tank_id, sensor_type=sensor_type)


@router.post("", response_model=SensorRead, dependencies=[Depends(require_roles("operator"))])
async def create_sensor(data: SensorCreate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.create_sensor(db, data)


@router.patch("/{sensor_id}", response_model=SensorRead, dependencies=[Depends(require_roles("operator"))])
async def update_sensor(sensor_id: UUID, data: SensorUpdate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.update_sensor(db, sensor_id, data)


@router.delete("/{sensor_id}", response_model=SensorRead, dependencies=[Depends(require_roles("operator"))])
async def deactivate_sensor(sensor_id: UUID, db: AsyncSession = Depends(get_db)):
    return await sensor_service.deactivate_sensor(db, sensor_id)
