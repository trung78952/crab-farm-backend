from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.mqtt_log import MqttLogRead
from app.services import mqtt_log_service

router = APIRouter()


@router.get("", response_model=list[MqttLogRead], dependencies=[Depends(require_roles("viewer", "operator"))])
async def list_mqtt_logs(
    topic: str | None = None,
    direction: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    since: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await mqtt_log_service.list_mqtt_logs(
        db,
        topic=topic,
        direction=direction,
        limit=limit,
        offset=offset,
        since=since,
    )
