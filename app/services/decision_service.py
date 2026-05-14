from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detection import Detection
from app.models.harvest import Harvest
from app.schemas.recheck_task import RecheckTaskCreate
from app.services.recheck_task_service import create_recheck_task
from app.services.realtime_service import realtime_service


async def handle_detection_decision(db: AsyncSession, detection: Detection, *, verification: bool = False) -> None:
    tank = detection.tank
    if tank is None:
        tank = await db.get(__import__("app.models.tank", fromlist=["Tank"]).Tank, detection.tank_id)
    if tank is None:
        return

    class_name = detection.class_name
    now = datetime.now(timezone.utc)

    if class_name == "crab_normal":
        tank.status = "normal"
        detection.action = "none"
    elif class_name == "crab_molting":
        tank.status = "molting"
        detection.action = "recheck"
        await create_recheck_task(
            db,
            RecheckTaskCreate(
                tank_id=tank.id,
                source_detection_id=detection.id,
                reason="molting",
                run_at=now + timedelta(minutes=settings.molting_recheck_minutes),
                priority=10,
            ),
        )
    elif class_name == "crab_soft_shell":
        tank.status = "soft_shell"
        if verification and detection.confidence >= settings.soft_shell_confidence_threshold:
            detection.action = "harvest"
            db.add(Harvest(tank_id=tank.id, detection_id=detection.id, status="queued", note="Auto queued after soft-shell verification"))
        else:
            detection.action = "recheck"
            await create_recheck_task(
                db,
                RecheckTaskCreate(
                    tank_id=tank.id,
                    source_detection_id=detection.id,
                    reason="suspected_soft_shell",
                    run_at=now + timedelta(seconds=settings.soft_shell_verify_seconds),
                    priority=5,
                ),
            )
    elif class_name in {"uncertain_or_bad_image", "bad_image", "uncertain"}:
        detection.action = "recheck"
        await create_recheck_task(
            db,
            RecheckTaskCreate(
                tank_id=tank.id,
                source_detection_id=detection.id,
                reason="bad_image" if class_name == "bad_image" else "uncertain",
                run_at=now + timedelta(minutes=settings.uncertain_recheck_minutes),
                priority=3,
            ),
        )
    elif class_name == "empty_tank":
        tank.status = "empty"
        detection.action = "none"

    await realtime_service.broadcast(
        "harvest_updated",
        {"tank_id": str(tank.id), "tank_status": tank.status, "detection_id": str(detection.id), "action": detection.action},
    )
