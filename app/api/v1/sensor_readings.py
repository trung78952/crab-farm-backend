from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.sensor import SensorReadingCreate, SensorReadingRead
from app.services import sensor_service

router = APIRouter()


@router.get("", response_model=list[SensorReadingRead])
async def list_sensor_readings(
    sensor_id: UUID | None = None,
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    return await sensor_service.list_sensor_readings(
        db,
        sensor_id=sensor_id,
        tank_id=tank_id,
        shelf_id=shelf_id,
        from_=from_,
        to=to,
        limit=limit,
    )


@router.post("", response_model=SensorReadingRead, dependencies=[Depends(require_roles("operator"))])
async def create_sensor_reading(data: SensorReadingCreate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.create_sensor_reading(db, data)


@router.get("/latest", response_model=list[SensorReadingRead])
async def latest_sensor_readings(
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await sensor_service.latest_sensor_readings(db, tank_id=tank_id, shelf_id=shelf_id)
