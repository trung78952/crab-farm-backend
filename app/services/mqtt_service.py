from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.motion_command import MotionCommand
from app.models.mqtt_log import MqttLog


def parse_mqtt_payload(payload_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        return {"raw": payload_text}

    if isinstance(payload, dict):
        return payload
    return {"value": payload}


async def log_mqtt_message(
    db: AsyncSession,
    *,
    direction: str,
    topic: str,
    payload: dict[str, Any],
    qos: int = 0,
) -> MqttLog:
    log = MqttLog(direction=direction, topic=topic, payload=payload, qos=qos)
    db.add(log)
    return log


async def handle_incoming_mqtt_message(topic: str, payload_text: str, qos: int = 0) -> None:
    payload = parse_mqtt_payload(payload_text)
    async with AsyncSessionLocal() as db:
        await log_mqtt_message(db, direction="subscribe", topic=topic, payload=payload, qos=qos)

        if topic == "farm/motion/ack":
            await _handle_motion_ack(db, payload)

        await db.commit()


async def _handle_motion_ack(db: AsyncSession, payload: dict[str, Any]) -> None:
    cmd_id = payload.get("cmd_id")
    if not cmd_id:
        return

    result = await db.execute(select(MotionCommand).where(MotionCommand.cmd_id == cmd_id))
    command = result.scalar_one_or_none()
    if command is None:
        return

    incoming_status = str(payload.get("status", "acknowledged")).lower()
    if incoming_status in {"done", "completed", "success"}:
        command.status = "done"
        command.completed_at = datetime.now(timezone.utc)
    elif incoming_status in {"failed", "error"}:
        command.status = "failed"
        command.completed_at = datetime.now(timezone.utc)
    else:
        command.status = "acknowledged"

    command.mqtt_response = payload
