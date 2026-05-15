from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detection import Detection
from app.models.harvest import Harvest
from app.models.scan_schedule import ScanSchedule
from app.models.tank import Tank
from app.services.realtime_service import realtime_service
from app.services.scan_schedule_service import complete_auto_schedules_for_tank, find_active_auto_schedule


async def handle_detection_decision(db: AsyncSession, detection: Detection, *, verification: bool = False) -> None:
    tank = detection.tank
    if tank is None:
        tank = await db.get(Tank, detection.tank_id)
    if tank is None:
        return

    class_name = detection.class_name
    now = datetime.now(timezone.utc)

    if class_name == "crab_normal":
        tank.status = "normal"
        detection.action = "none"
        if detection.confidence >= settings.ai_confidence_threshold:
            await complete_auto_schedules_for_tank(
                db,
                tank_id=tank.id,
                schedule_types={"auto_recheck", "auto_verify"},
                stop_condition="soft_shell_or_normal",
            )

    elif class_name == "crab_molting":
        tank.status = "molting"
        detection.action = "recheck"
        await _ensure_auto_recheck(
            db,
            tank=tank,
            reason="molting",
            parent_detection_id=detection.id,
            interval_minutes=settings.molting_recheck_minutes,
            priority=10,
            stop_condition="soft_shell_or_normal",
            next_run_at=now + timedelta(minutes=settings.molting_recheck_minutes),
        )

    elif class_name == "crab_soft_shell":
        if verification and detection.confidence >= settings.soft_shell_confidence_threshold:
            tank.status = "soft_shell"
            detection.action = "harvest"
            harvest = Harvest(
                tank_id=tank.id,
                detection_id=detection.id,
                status="queued",
                note="Auto queued after soft-shell verification",
            )
            db.add(harvest)
            await db.flush()
            await complete_auto_schedules_for_tank(
                db,
                tank_id=tank.id,
                schedule_types={"auto_recheck", "auto_verify"},
                stop_condition="verified_soft_shell",
            )
            await realtime_service.broadcast(
                "harvest_updated",
                {"id": str(harvest.id), "status": harvest.status, "tank_id": str(harvest.tank_id)},
            )
        elif detection.confidence >= settings.soft_shell_confidence_threshold:
            tank.status = "soft_shell"
            detection.action = "recheck"
            await _ensure_auto_verify(
                db,
                tank=tank,
                parent_detection_id=detection.id,
                next_run_at=now + timedelta(seconds=settings.soft_shell_verify_seconds),
            )
        else:
            detection.action = "recheck"
            await _ensure_auto_recheck(
                db,
                tank=tank,
                reason="suspected_soft_shell",
                parent_detection_id=detection.id,
                interval_minutes=settings.uncertain_recheck_minutes,
                priority=10,
                stop_condition="soft_shell_or_normal",
                next_run_at=now + timedelta(minutes=settings.uncertain_recheck_minutes),
            )

    elif class_name in {"uncertain_or_bad_image", "bad_image", "uncertain"}:
        reason = "bad_image" if class_name == "bad_image" else "uncertain"
        detection.action = "recheck"
        await _ensure_auto_recheck(
            db,
            tank=tank,
            reason=reason,
            parent_detection_id=detection.id,
            interval_minutes=settings.uncertain_recheck_minutes,
            priority=15 if reason == "bad_image" else 10,
            stop_condition="soft_shell_or_normal",
            next_run_at=now + timedelta(minutes=settings.uncertain_recheck_minutes),
        )

    elif class_name == "empty_tank":
        tank.status = "empty"
        detection.action = "none"
        if detection.confidence >= settings.ai_confidence_threshold:
            await complete_auto_schedules_for_tank(
                db,
                tank_id=tank.id,
                schedule_types={"auto_recheck", "auto_verify"},
                stop_condition="empty_tank",
            )

    await realtime_service.broadcast(
        "tank_updated",
        {"id": str(tank.id), "status": tank.status, "detection_id": str(detection.id), "action": detection.action},
    )


async def _ensure_auto_recheck(
    db: AsyncSession,
    *,
    tank: Tank,
    reason: str,
    parent_detection_id: UUID,
    interval_minutes: int,
    priority: int,
    stop_condition: str,
    next_run_at: datetime,
) -> ScanSchedule:
    schedule = await find_active_auto_schedule(db, tank_id=tank.id, schedule_type="auto_recheck", auto_reason=reason)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auto_recheck_expire_hours)
    if schedule is None:
        schedule = ScanSchedule(
            shelf_id=tank.shelf_id,
            name=f"Auto recheck {tank.code} ({reason})",
            schedule_type="auto_recheck",
            tag="AUTO",
            scan_mode="single_tank",
            tank_ids=[str(tank.id)],
            interval_minutes=interval_minutes,
            priority=priority,
            is_active=True,
            run_once=False,
            run_count=0,
            max_runs=settings.auto_recheck_max_runs,
            next_run_at=next_run_at,
            expires_at=expires_at,
            stop_condition=stop_condition,
            created_by_system=True,
            auto_reason=reason,
            parent_detection_id=parent_detection_id,
        )
        db.add(schedule)
        await db.flush()
        await realtime_service.broadcast(
            "scan_schedule_created",
            {"id": str(schedule.id), "tag": schedule.tag, "schedule_type": schedule.schedule_type, "auto_reason": schedule.auto_reason},
        )
        return schedule

    schedule.next_run_at = next_run_at
    schedule.interval_minutes = interval_minutes
    schedule.priority = min(schedule.priority, priority)
    schedule.max_runs = schedule.max_runs or settings.auto_recheck_max_runs
    schedule.expires_at = schedule.expires_at or expires_at
    schedule.parent_detection_id = schedule.parent_detection_id or parent_detection_id
    await realtime_service.broadcast(
        "scan_schedule_updated",
        {"id": str(schedule.id), "next_run_at": schedule.next_run_at.isoformat(), "auto_reason": schedule.auto_reason},
    )
    return schedule


async def _ensure_auto_verify(
    db: AsyncSession,
    *,
    tank: Tank,
    parent_detection_id: UUID,
    next_run_at: datetime,
) -> ScanSchedule:
    schedule = await find_active_auto_schedule(db, tank_id=tank.id, schedule_type="auto_verify", auto_reason="suspected_soft_shell")
    if schedule is None:
        schedule = ScanSchedule(
            shelf_id=tank.shelf_id,
            name=f"Auto verify {tank.code}",
            schedule_type="auto_verify",
            tag="AUTO",
            scan_mode="single_tank",
            tank_ids=[str(tank.id)],
            interval_minutes=None,
            priority=5,
            is_active=True,
            run_once=True,
            run_count=0,
            max_runs=1,
            next_run_at=next_run_at,
            stop_condition="verified_soft_shell",
            created_by_system=True,
            auto_reason="suspected_soft_shell",
            parent_detection_id=parent_detection_id,
        )
        db.add(schedule)
        await db.flush()
        await realtime_service.broadcast(
            "scan_schedule_created",
            {"id": str(schedule.id), "tag": schedule.tag, "schedule_type": schedule.schedule_type, "auto_reason": schedule.auto_reason},
        )
        return schedule

    schedule.next_run_at = next_run_at
    schedule.priority = min(schedule.priority, 5)
    schedule.parent_detection_id = schedule.parent_detection_id or parent_detection_id
    await realtime_service.broadcast(
        "scan_schedule_updated",
        {"id": str(schedule.id), "next_run_at": schedule.next_run_at.isoformat(), "auto_reason": schedule.auto_reason},
    )
    return schedule
