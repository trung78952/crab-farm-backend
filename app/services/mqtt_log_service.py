from datetime import datetime

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mqtt_log import MqttLog


async def list_mqtt_logs(
    db: AsyncSession,
    *,
    topic: str | None = None,
    direction: str | None = None,
    limit: int = 100,
    offset: int = 0,
    since: datetime | None = None,
) -> list[MqttLog]:
    stmt = select(MqttLog).order_by(MqttLog.created_at.desc()).offset(offset).limit(limit)
    if topic:
        stmt = stmt.where(MqttLog.topic == topic)
    if direction:
        stmt = stmt.where(MqttLog.direction == direction)
    if since:
        stmt = stmt.where(MqttLog.created_at >= since)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_topics(db: AsyncSession) -> list[str]:
    result = await db.execute(select(distinct(MqttLog.topic)).order_by(MqttLog.topic))
    return [topic for topic in result.scalars().all() if topic]
