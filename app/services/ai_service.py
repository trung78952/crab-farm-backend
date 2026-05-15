from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detection import Detection
from app.models.image import Image
from app.schemas.ai import AiStatusRead
from app.services.decision_service import handle_detection_decision
from app.services.model_registry_service import get_or_create_active_model
from app.services.realtime_service import realtime_service


def ai_status() -> AiStatusRead:
    return AiStatusRead(
        enabled=settings.ai_enabled,
        mock_mode=settings.ai_mock_mode,
        simulation_mode=settings.simulation_mode,
        active_model_path=settings.ai_model_path,
        active_model_version=settings.ai_model_version,
        confidence_threshold=settings.ai_confidence_threshold,
        image_size=settings.ai_image_size,
    )


async def detect_image(db: AsyncSession, image_id: UUID, *, verification: bool = False) -> Detection:
    image = await db.get(Image, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    model = await get_or_create_active_model(db)
    class_name = "uncertain_or_bad_image"
    confidence = 0.0
    bbox: dict = {}

    if settings.ai_mock_mode or settings.simulation_mode:
        class_name = "crab_normal"
        confidence = 0.99
    elif settings.ai_enabled:
        model_path = Path(model.model_path)
        if not model_path.exists():
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Active AI model file not found")
        try:
            from ultralytics import YOLO

            yolo = YOLO(str(model_path))
            results = yolo(str(image.image_path), imgsz=settings.ai_image_size, conf=settings.ai_confidence_threshold, verbose=False)
            if results and len(results[0].boxes) > 0:
                best_idx = int(results[0].boxes.conf.argmax().item())
                box = results[0].boxes[best_idx]
                cls_idx = int(box.cls[0].item())
                names = results[0].names
                class_name = names.get(cls_idx, str(cls_idx))
                confidence = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()
                bbox = {"x1": xyxy[0], "y1": xyxy[1], "x2": xyxy[2], "y2": xyxy[3]}
        except ImportError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ultralytics is not installed") from exc

    detection = Detection(
        tank_id=image.tank_id,
        image_id=image.id,
        class_name=_normalize_class_name(class_name),
        confidence=confidence,
        bbox=bbox,
        action="none",
        model_name=model.name,
        model_version=model.version,
        is_simulation=settings.simulation_mode or settings.ai_mock_mode,
        detected_at=datetime.now(timezone.utc),
    )
    db.add(detection)
    await db.flush()
    await handle_detection_decision(db, detection, verification=verification)
    await db.commit()
    await db.refresh(detection)
    await realtime_service.broadcast(
        "detection_created",
        {"id": str(detection.id), "tank_id": str(detection.tank_id), "class_name": detection.class_name, "confidence": detection.confidence},
    )
    return detection


def _normalize_class_name(class_name: str) -> str:
    aliases = {
        "crab": "crab_normal",
        "normal_crab": "crab_normal",
        "molting": "crab_molting",
        "molting_crab": "crab_molting",
        "soft_shell_crab": "crab_soft_shell",
        "softshell_crab": "crab_soft_shell",
        "bad_image": "uncertain_or_bad_image",
        "uncertain": "uncertain_or_bad_image",
    }
    return aliases.get(class_name, class_name)
