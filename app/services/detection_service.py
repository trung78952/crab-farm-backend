from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection
from app.models.harvest import Harvest
from app.models.image import Image
from app.schemas.detection import DetectionMockCreate
from app.services.tank_service import get_tank


class DetectionEngine:
    async def detect_image(self, image_path: str) -> list[dict]:
        raise NotImplementedError("Real detection engine is not implemented in MVP")


async def create_mock_detection(db: AsyncSession, data: DetectionMockCreate) -> Detection:
    tank = await get_tank(db, data.tank_id)
    image = await db.get(Image, data.image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    if image.tank_id != data.tank_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image does not belong to tank")

    is_soft_shell = data.class_name == "soft_shell_crab" and data.confidence >= 0.85
    action = data.action or ("harvest" if is_soft_shell else "none")

    detection = Detection(
        tank_id=data.tank_id,
        image_id=data.image_id,
        class_name=data.class_name,
        confidence=data.confidence,
        bbox=data.bbox,
        action=action,
        model_name=data.model_name,
    )
    db.add(detection)
    await db.flush()

    if is_soft_shell:
        tank.status = "soft_shell"
        db.add(Harvest(tank_id=tank.id, detection_id=detection.id, status="queued", note="Auto queued by mock detection"))
    elif data.class_name in {"molting_crab", "molting"}:
        tank.status = "molting"
    elif data.class_name in {"crab", "normal_crab"}:
        tank.status = "normal"

    await db.commit()
    await db.refresh(detection)
    return detection


async def list_detections(db: AsyncSession) -> list[Detection]:
    result = await db.execute(select(Detection).order_by(Detection.created_at.desc()))
    return list(result.scalars().all())


async def list_detections_by_tank(db: AsyncSession, tank_id: UUID) -> list[Detection]:
    await get_tank(db, tank_id)
    result = await db.execute(
        select(Detection).where(Detection.tank_id == tank_id).order_by(Detection.created_at.desc())
    )
    return list(result.scalars().all())
