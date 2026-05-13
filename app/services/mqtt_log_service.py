from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mqtt_log import MqttLog


async def list_mqtt_logs(db: AsyncSession, limit: int = 100) -> list[MqttLog]:
    result = await db.execute(select(MqttLog).order_by(MqttLog.created_at.desc()).limit(limit))
    return list(result.scalars().all())
