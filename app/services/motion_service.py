from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mqtt import mqtt_manager
from app.core.config import settings
from app.models.motion_command import MotionCommand
from app.models.shelf import Shelf
from app.schemas.motion import GCodeRequest
from app.services.mqtt_service import log_mqtt_message
from app.services.tank_service import get_tank
from app.utils.id_generator import generate_command_id

DEFAULT_MOTION_CMD_TOPIC = "farm/motion/cmd"


async def home(db: AsyncSession) -> MotionCommand:
    cmd_id = generate_command_id("HOME")
    payload = {"cmd_id": cmd_id, "type": "home"}
    return await _create_publish_command(db, cmd_id=cmd_id, command_type="home", payload=payload)


async def move_to_tank(db: AsyncSession, tank_id: UUID, speed: int = 3000) -> MotionCommand:
    tank = await get_tank(db, tank_id)
    cmd_id = generate_command_id("CMD")
    shelf = await _get_tank_shelf(db, tank.shelf_id)
    payload = {
        "cmd_id": cmd_id,
        "shelf_code": shelf.code if shelf else None,
        "tank_code": tank.code,
        "type": "move_to_tank",
        "tank_id": tank.code,
        "x": tank.x_position,
        "y": tank.y_position,
        "z": tank.z_position,
        "speed": speed,
    }
    return await _create_publish_command(
        db,
        cmd_id=cmd_id,
        command_type="move_to_tank",
        payload=payload,
        tank_id=tank.id,
        topic=_motion_topic(shelf),
    )


async def send_gcode(db: AsyncSession, data: GCodeRequest) -> MotionCommand:
    cmd_id = generate_command_id("GCODE")
    payload = {"cmd_id": cmd_id, "type": "gcode", "lines": data.lines}
    return await _create_publish_command(db, cmd_id=cmd_id, command_type="gcode", payload=payload)


async def emergency_stop(db: AsyncSession) -> MotionCommand:
    cmd_id = generate_command_id("ESTOP")
    payload = {"cmd_id": cmd_id, "type": "emergency_stop"}
    return await _create_publish_command(db, cmd_id=cmd_id, command_type="emergency_stop", payload=payload)


async def create_harvest_motion_command(db: AsyncSession, tank_id: UUID, harvest_id: UUID) -> MotionCommand:
    tank = await get_tank(db, tank_id)
    cmd_id = generate_command_id("HARVEST")
    shelf = await _get_tank_shelf(db, tank.shelf_id)
    payload = {
        "cmd_id": cmd_id,
        "shelf_code": shelf.code if shelf else None,
        "tank_code": tank.code,
        "type": "harvest",
        "harvest_id": str(harvest_id),
        "tank_id": tank.code,
        "x": tank.x_position,
        "y": tank.y_position,
        "z": tank.z_position,
    }
    return await _create_publish_command(
        db,
        cmd_id=cmd_id,
        command_type="harvest",
        payload=payload,
        tank_id=tank.id,
        topic=_motion_topic(shelf),
    )


async def list_commands(db: AsyncSession) -> list[MotionCommand]:
    result = await db.execute(select(MotionCommand).order_by(MotionCommand.created_at.desc()))
    return list(result.scalars().all())


async def get_command_by_cmd_id(db: AsyncSession, cmd_id: str) -> MotionCommand:
    result = await db.execute(select(MotionCommand).where(MotionCommand.cmd_id == cmd_id))
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Motion command not found")
    return command


async def _create_publish_command(
    db: AsyncSession,
    *,
    cmd_id: str,
    command_type: str,
    payload: dict,
    tank_id: UUID | None = None,
    topic: str | None = None,
) -> MotionCommand:
    mqtt_topic = topic or DEFAULT_MOTION_CMD_TOPIC
    command = MotionCommand(
        cmd_id=cmd_id,
        command_type=command_type,
        tank_id=tank_id,
        payload=payload,
        status="pending",
        mqtt_topic=mqtt_topic,
    )
    db.add(command)
    await db.flush()

    if settings.simulation_mode and not settings.mqtt_simulate_publish:
        command.status = "simulated"
        command.mqtt_response = {"simulation": True}
    else:
        try:
            mqtt_manager.publish_json(mqtt_topic, payload)
        except Exception as exc:
            command.status = "failed"
            command.mqtt_response = {"error": str(exc)}
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to publish MQTT command: {exc}",
            ) from exc
        command.status = "sent"
    command.sent_at = datetime.now(timezone.utc)
    await log_mqtt_message(db, direction="publish", topic=mqtt_topic, payload=payload)
    await db.commit()
    await db.refresh(command)
    from app.services.realtime_service import realtime_service

    await realtime_service.broadcast(
        "motion_command_created",
        {"id": str(command.id), "cmd_id": command.cmd_id, "command_type": command.command_type, "status": command.status},
    )
    if command.command_type == "emergency_stop":
        await realtime_service.broadcast("emergency_stop_triggered", {"id": str(command.id), "cmd_id": command.cmd_id, "status": command.status})
    return command


async def _get_tank_shelf(db: AsyncSession, shelf_id: UUID | None) -> Shelf | None:
    if shelf_id is None:
        return None
    return await db.get(Shelf, shelf_id)


def _motion_topic(shelf: Shelf | None) -> str:
    if shelf is None:
        return DEFAULT_MOTION_CMD_TOPIC
    return f"farm/shelf/{shelf.code}/motion/cmd"
