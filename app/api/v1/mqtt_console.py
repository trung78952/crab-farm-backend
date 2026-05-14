from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.core.mqtt import mqtt_manager
from app.schemas.mqtt_console import MqttPublishRequest
from app.schemas.mqtt_log import MqttLogRead
from app.services import mqtt_log_service
from app.services.mqtt_service import log_mqtt_message

router = APIRouter()


@router.get("/logs", response_model=list[MqttLogRead], dependencies=[Depends(require_roles("viewer", "operator"))])
async def list_logs(
    topic: str | None = None,
    direction: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await mqtt_log_service.list_mqtt_logs(db, topic=topic, direction=direction, limit=limit, offset=offset)


@router.get("/topics", response_model=list[str], dependencies=[Depends(require_roles("viewer", "operator"))])
async def list_topics(db: AsyncSession = Depends(get_db)):
    return await mqtt_log_service.list_topics(db)


@router.post("/publish", response_model=MqttLogRead, dependencies=[Depends(require_roles("operator"))])
async def publish(data: MqttPublishRequest, db: AsyncSession = Depends(get_db)):
    payload = data.payload if isinstance(data.payload, dict) else {"raw": data.payload}
    mqtt_manager.publish_json(data.topic, payload, qos=data.qos)
    log = await log_mqtt_message(
        db,
        direction="publish",
        topic=data.topic,
        payload=payload,
        raw_payload=None if isinstance(data.payload, dict) else data.payload,
        qos=data.qos,
        retain=data.retain,
    )
    await db.commit()
    await db.refresh(log)
    return log
