from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection
from app.models.harvest import Harvest
from app.models.image import Image
from app.schemas.detection import DetectionMockCreate, DetectionVerifyRequest
from app.services.decision_service import handle_detection_decision
from app.services.realtime_service import realtime_service
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

    action = data.action or "none"

    detection = Detection(
        tank_id=data.tank_id,
        image_id=data.image_id,
        class_name=data.class_name,
        confidence=data.confidence,
        bbox=data.bbox,
        action=action,
        model_name=data.model_name,
        model_version="mock",
        is_simulation=True,
    )
    db.add(detection)
    await db.flush()

    if data.class_name in {"soft_shell_crab", "crab_soft_shell"}:
        detection.class_name = "crab_soft_shell"
    elif data.class_name in {"molting_crab", "molting", "crab_molting"}:
        detection.class_name = "crab_molting"
    elif data.class_name in {"crab", "normal_crab", "crab_normal"}:
        detection.class_name = "crab_normal"

    await handle_detection_decision(db, detection)

    await db.commit()
    await db.refresh(detection)
    await realtime_service.broadcast(
        "detection_created",
        {"id": str(detection.id), "tank_id": str(detection.tank_id), "class_name": detection.class_name},
    )
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


async def verify_detection(db: AsyncSession, detection_id: UUID, data: DetectionVerifyRequest, user_id: UUID) -> Detection:
    detection = await db.get(Detection, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")

    detection.is_verified = True
    detection.human_label = data.human_label or detection.class_name
    detection.verified_by = user_id
    from datetime import datetime, timezone

    detection.verified_at = datetime.now(timezone.utc)
    if not data.is_correct and data.human_label:
        detection.class_name = data.human_label
    await db.commit()
    await db.refresh(detection)
    await realtime_service.broadcast(
        "detection_created",
        {"id": str(detection.id), "verified": detection.is_verified, "human_label": detection.human_label},
    )
    return detection
