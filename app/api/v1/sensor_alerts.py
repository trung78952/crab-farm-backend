from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.sensor import SensorAlertRead
from app.services import sensor_service

router = APIRouter()


@router.get("", response_model=list[SensorAlertRead])
async def list_sensor_alerts(
    status: str | None = Query(None),
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await sensor_service.list_sensor_alerts(db, status_filter=status, tank_id=tank_id, shelf_id=shelf_id)


@router.post("/{alert_id}/ack", response_model=SensorAlertRead, dependencies=[Depends(require_roles("operator"))])
async def acknowledge_sensor_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    return await sensor_service.acknowledge_sensor_alert(db, alert_id)


@router.post("/{alert_id}/resolve", response_model=SensorAlertRead, dependencies=[Depends(require_roles("operator"))])
async def resolve_sensor_alert(alert_id: UUID, db: AsyncSession = Depends(get_db)):
    return await sensor_service.resolve_sensor_alert(db, alert_id)
