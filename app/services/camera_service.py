from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.mqtt import mqtt_manager
from app.models.device import Device
from app.models.image import Image
from app.services.mqtt_service import log_mqtt_message
from app.services.tank_service import get_tank
from app.utils.id_generator import generate_command_id

DEFAULT_CAMERA_CMD_TOPIC = "farm/camera/cmd"


async def capture_tank_image(db: AsyncSession, tank_id: UUID) -> dict:
    tank = await get_tank(db, tank_id)
    cmd_id = generate_command_id("CAM")
    shelf = await db.get(__import__("app.models.shelf", fromlist=["Shelf"]).Shelf, tank.shelf_id) if tank.shelf_id else None
    topic = f"farm/shelf/{shelf.code}/camera/cmd" if shelf else DEFAULT_CAMERA_CMD_TOPIC
    payload = {
        "cmd_id": cmd_id,
        "shelf_code": shelf.code if shelf else None,
        "tank_code": tank.code,
        "type": "capture",
        "tank_id": tank.code,
    }

    if not (settings.simulation_mode and not settings.mqtt_simulate_publish):
        try:
            mqtt_manager.publish_json(topic, payload)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to publish camera command: {exc}",
            ) from exc

    await log_mqtt_message(db, direction="publish", topic=topic, payload=payload)
    await db.commit()
    return {"cmd_id": cmd_id, "topic": topic, "payload": payload}


async def upload_image(
    db: AsyncSession,
    *,
    tank_id: UUID,
    file: UploadFile,
    device_id: UUID | None = None,
) -> Image:
    await get_tank(db, tank_id)
    if device_id is not None and await db.get(Device, device_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    raw_dir = Path(settings.storage_dir) / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}{suffix}"
    target_path = raw_dir / filename

    async with aiofiles.open(target_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    image_url = f"{settings.public_storage_url}/raw/{filename}"
    image = Image(
        tank_id=tank_id,
        device_id=device_id,
        image_path=str(target_path),
        image_url=image_url,
        kind="raw",
        is_simulation=settings.simulation_mode,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def list_images(db: AsyncSession, tank_id: UUID | None = None) -> list[Image]:
    stmt = select(Image).order_by(Image.created_at.desc())
    if tank_id is not None:
        stmt = stmt.where(Image.tank_id == tank_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())
