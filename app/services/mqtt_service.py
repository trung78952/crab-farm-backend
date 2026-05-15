from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.motion_command import MotionCommand
from app.models.mqtt_log import MqttLog

logger = logging.getLogger(__name__)


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
    raw_payload: str | None = None,
    qos: int = 0,
    retain: bool | None = None,
) -> MqttLog:
    log = MqttLog(direction=direction, topic=topic, payload=payload, raw_payload=raw_payload, qos=qos, retain=retain)
    db.add(log)
    await db.flush()
    from app.services.realtime_service import realtime_service

    await realtime_service.broadcast(
        "mqtt_log_created",
        {
            "id": str(log.id),
            "direction": log.direction,
            "topic": log.topic,
            "payload": log.payload,
            "raw_payload": log.raw_payload,
            "qos": log.qos,
            "retain": log.retain,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        },
    )
    return log


async def handle_incoming_mqtt_message(topic: str, payload_text: str, qos: int = 0, retain: bool | None = None) -> None:
    payload = parse_mqtt_payload(payload_text)
    async with AsyncSessionLocal() as db:
        await log_mqtt_message(db, direction="subscribe", topic=topic, payload=payload, raw_payload=payload_text, qos=qos, retain=retain)

        if topic.endswith("/motion/ack") or topic == "farm/motion/ack":
            await _handle_motion_ack(db, payload)
        elif topic.endswith("/camera/result") or topic == "farm/camera/result":
            await _handle_camera_result(db, payload)
        elif topic.endswith("/device/status"):
            await _handle_device_status(db, payload)
        elif _is_sensor_topic(topic):
            try:
                from app.services.sensor_service import create_sensor_reading_from_mqtt

                await create_sensor_reading_from_mqtt(db, topic, payload)
            except Exception:
                logger.exception("Failed to process sensor MQTT message topic=%s", topic)

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
    from app.services.realtime_service import realtime_service

    await realtime_service.broadcast(
        "motion_command_updated",
        {
            "id": str(command.id),
            "cmd_id": command.cmd_id,
            "status": command.status,
            "mqtt_response": command.mqtt_response,
        },
    )


async def _handle_device_status(db: AsyncSession, payload: dict[str, Any]) -> None:
    device_code = payload.get("device_code") or payload.get("code")
    if not device_code:
        return

    from app.models.device import Device
    from app.services.realtime_service import realtime_service

    result = await db.execute(select(Device).where(Device.code == device_code))
    device = result.scalar_one_or_none()
    if device is None:
        return

    device.status = str(payload.get("status", device.status))
    device.last_seen_at = datetime.now(timezone.utc)
    await realtime_service.broadcast(
        "device_status_updated",
        {"id": str(device.id), "code": device.code, "status": device.status, "last_seen_at": device.last_seen_at.isoformat()},
    )


async def _handle_camera_result(db: AsyncSession, payload: dict[str, Any]) -> None:
    cmd_id = payload.get("cmd_id")
    if not cmd_id:
        return

    from uuid import UUID

    from app.models.image import Image
    from app.models.scan_job_item import ScanJobItem
    from app.models.tank import Tank
    from app.services.realtime_service import realtime_service

    result = await db.execute(select(ScanJobItem).where(ScanJobItem.camera_command_id == cmd_id))
    item = result.scalar_one_or_none()
    if item is None:
        return

    image_id = payload.get("image_id")
    if image_id:
        try:
            item.image_id = UUID(str(image_id))
        except ValueError:
            item.error_message = f"Invalid image_id from camera result: {image_id}"
    elif payload.get("image_url") and payload.get("image_path"):
        tank = await db.get(Tank, item.tank_id)
        image = Image(
            tank_id=item.tank_id,
            image_path=str(payload["image_path"]),
            image_url=str(payload["image_url"]),
            kind="raw",
            is_simulation=False,
        )
        db.add(image)
        await db.flush()
        item.image_id = image.id
        if tank is not None:
            tank.last_checked_at = datetime.now(timezone.utc)

    if item.image_id is not None:
        item.status = "image_received"
        await realtime_service.broadcast(
            "scan_job_item_updated",
            {"id": str(item.id), "status": item.status, "image_id": str(item.image_id)},
        )


def _is_sensor_topic(topic: str) -> bool:
    parts = topic.split("/")
    return len(parts) >= 5 and parts[0] == "farm" and "sensor" in parts
