from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.recheck_task import RecheckTask
from app.models.scan_job import ScanJob
from app.models.scan_job_item import ScanJobItem
from app.models.scan_schedule import ScanSchedule
from app.models.tank import Tank
from app.services import camera_service, motion_service
from app.services.realtime_service import realtime_service

logger = logging.getLogger(__name__)


async def run_all(db: AsyncSession, shelf_id: UUID | None = None) -> list[ScanJob]:
    tanks = await _load_all_tanks(db, shelf_id=shelf_id)
    grouped: dict[UUID | None, list[Tank]] = defaultdict(list)
    for tank in tanks:
        grouped[tank.shelf_id if shelf_id is None else shelf_id].append(tank)

    jobs: list[ScanJob] = []
    for group_shelf_id, group_tanks in grouped.items():
        if not group_tanks:
            continue
        job = await create_scan_job(
            db,
            scan_mode="all_tanks",
            tanks=group_tanks,
            job_type="manual_scan",
            shelf_id=group_shelf_id,
            priority=20,
        )
        jobs.append(await get_scan_job(db, job.id))
    return jobs


async def run_tank(db: AsyncSession, tank_id: UUID) -> ScanJob:
    tank = await db.get(Tank, tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")

    job = await create_scan_job(
        db,
        scan_mode="single_tank",
        tanks=[tank],
        job_type="manual_scan",
        shelf_id=tank.shelf_id,
        priority=20,
    )
    return await get_scan_job(db, job.id)


async def list_scan_jobs(db: AsyncSession) -> list[ScanJob]:
    result = await db.execute(
        select(ScanJob)
        .options(selectinload(ScanJob.items))
        .order_by(ScanJob.created_at.desc())
    )
    return list(result.scalars().unique().all())


async def get_scan_job(db: AsyncSession, job_id: UUID) -> ScanJob:
    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.id == job_id)
        .options(selectinload(ScanJob.items))
    )
    job = result.scalars().unique().one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")
    return job


async def create_scan_job(
    db: AsyncSession,
    *,
    scan_mode: str,
    tanks: list[Tank],
    schedule_id: UUID | None = None,
    shelf_id: UUID | None = None,
    job_type: str = "manual_scan",
    priority: int = 100,
) -> ScanJob:
    inferred_shelf_id = shelf_id
    if inferred_shelf_id is None:
        shelf_ids = {tank.shelf_id for tank in tanks if tank.shelf_id is not None}
        inferred_shelf_id = next(iter(shelf_ids)) if len(shelf_ids) == 1 else None
    job = ScanJob(
        schedule_id=schedule_id,
        shelf_id=inferred_shelf_id,
        job_type=job_type,
        status="queued",
        priority=priority,
        scan_mode=scan_mode,
        total_tanks=len(tanks),
        completed_tanks=0,
        failed_tanks=0,
        is_simulation=settings.simulation_mode,
    )
    db.add(job)
    await db.flush()

    for tank in tanks:
        db.add(ScanJobItem(scan_job_id=job.id, tank_id=tank.id, status="queued"))

    await db.commit()
    await realtime_service.broadcast(
        "scan_job_created",
        {
            "id": str(job.id),
            "status": job.status,
            "shelf_id": str(job.shelf_id) if job.shelf_id else None,
            "job_type": job.job_type,
            "priority": job.priority,
        },
    )
    return job


async def create_scan_job_from_schedule(db: AsyncSession, schedule: ScanSchedule) -> ScanJob | None:
    tanks = await _load_tanks_for_schedule(db, schedule)
    if schedule.schedule_type == "user_periodic":
        tanks = _filter_recently_scanned(tanks)
    if not tanks:
        return None

    job_type = "scheduled_scan" if schedule.schedule_type == "user_periodic" else schedule.schedule_type
    job_scan_mode = "all_tanks" if schedule.scan_mode == "single_shelf" else schedule.scan_mode
    return await create_scan_job(
        db,
        scan_mode=job_scan_mode,
        tanks=tanks,
        schedule_id=schedule.id,
        shelf_id=schedule.shelf_id,
        job_type=job_type,
        priority=schedule.priority,
    )


async def create_recheck_scan_job(db: AsyncSession, task: RecheckTask) -> ScanJob:
    tank = await db.get(Tank, task.tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")
    return await create_scan_job(
        db,
        scan_mode="single_tank",
        tanks=[tank],
        shelf_id=tank.shelf_id,
        job_type="auto_recheck" if task.reason != "suspected_soft_shell" else "auto_verify",
        priority=task.priority,
    )


def start_scan_job_background(job_id: UUID) -> asyncio.Task:
    task = asyncio.create_task(process_scan_job(job_id))
    task.add_done_callback(_log_background_scan_error)
    return task


def _log_background_scan_error(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        return
    except Exception:
        logger.exception("Background scan job failed")


async def process_scan_job(job_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(ScanJob, job_id)
        if job is None or job.status == "cancelled":
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()
        await realtime_service.broadcast("scan_job_updated", {"id": str(job.id), "status": job.status})

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScanJobItem)
            .where(ScanJobItem.scan_job_id == job_id)
            .order_by(ScanJobItem.created_at)
        )
        items = list(result.scalars().all())

    for item in items:
        try:
            await process_scan_job_item(item.id)
        except TimeoutError as exc:
            await _finish_item(item.id, "timeout", str(exc))
        except Exception as exc:
            logger.exception("Scan job item failed")
            await _finish_item(item.id, "failed", str(exc))

    async with AsyncSessionLocal() as db:
        job = await db.get(ScanJob, job_id)
        if job is None:
            return
        result = await db.execute(select(ScanJobItem).where(ScanJobItem.scan_job_id == job_id))
        statuses = [item.status for item in result.scalars().all()]
        job.completed_tanks = statuses.count("success")
        job.failed_tanks = len([item_status for item_status in statuses if item_status in {"failed", "timeout"}])
        job.status = _final_job_status(statuses, job.is_simulation)
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await realtime_service.broadcast(
            "scan_job_updated",
            {
                "id": str(job.id),
                "status": job.status,
                "completed_tanks": job.completed_tanks,
                "failed_tanks": job.failed_tanks,
            },
        )


async def process_scan_job_item(item_id: UUID) -> None:
    command_id: UUID | None = None
    await _set_item_status(item_id, "moving", started=True)

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        command = await motion_service.move_to_tank(db, item.tank_id)
        command_id = command.id
        item.motion_command_id = command.id
        if settings.simulation_mode:
            item.status = "simulated"
            item.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await _broadcast_item(item)
            return
        item.status = "waiting_for_motion"
        await db.commit()
        await _broadcast_item(item)

    try:
        await wait_for_motion_done(command_id)
    except TimeoutError as exc:
        await _finish_item(item_id, "timeout", str(exc))
        return
    except RuntimeError as exc:
        await _finish_item(item_id, "failed", str(exc))
        return

    await _set_item_status(item_id, "motion_done")
    await asyncio.sleep(settings.motion_settle_ms / 1000)

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = "capturing"
        await db.commit()
        await _broadcast_item(item)
        try:
            camera_cmd = await camera_service.capture_tank_image(db, item.tank_id)
        except Exception as exc:
            await _finish_item(item_id, "failed", f"Camera capture command failed: {exc}")
            return
        item.camera_command_id = camera_cmd["cmd_id"]
        item.status = "waiting_for_camera"
        await db.commit()
        await _broadcast_item(item)

    image_id = await wait_for_camera_result(item_id)
    if image_id is None:
        await _finish_item(item_id, "timeout", "Camera result/image not received")
        return

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.image_id = image_id
        item.status = "image_received"
        await db.commit()
        await _broadcast_item(item)

    await _set_item_status(item_id, "detecting")
    try:
        detection_id = await asyncio.wait_for(run_detection(item_id, image_id), timeout=settings.ai_timeout_seconds)
    except asyncio.TimeoutError:
        await _finish_item(item_id, "timeout", "AI detection timed out")
        return

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        tank = await db.get(Tank, item.tank_id)
        if tank is not None:
            tank.last_checked_at = datetime.now(timezone.utc)
        item.detection_id = detection_id
        if detection_id is None:
            item.status = "failed"
            item.error_message = "Detection not completed"
        else:
            item.status = "success"
        item.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await _broadcast_item(item)


async def wait_for_motion_done(command_id: UUID | None) -> None:
    if command_id is None:
        raise RuntimeError("Motion command was not created")
    deadline = datetime.now(timezone.utc).timestamp() + settings.motion_timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        async with AsyncSessionLocal() as db:
            command = await db.get(__import__("app.models.motion_command", fromlist=["MotionCommand"]).MotionCommand, command_id)
            if command is not None and command.status == "done":
                return
            if command is not None and command.status in {"failed", "timeout"}:
                raise RuntimeError(f"Motion command {command.cmd_id} {command.status}")
        await asyncio.sleep(0.5)
    raise TimeoutError("Motion command timed out waiting for DONE")


async def wait_for_camera_result(item_id: UUID) -> UUID | None:
    deadline = datetime.now(timezone.utc).timestamp() + settings.camera_timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        async with AsyncSessionLocal() as db:
            item = await db.get(ScanJobItem, item_id)
            if item is not None and item.image_id is not None:
                return item.image_id
        await asyncio.sleep(0.5)
    return None


async def run_detection(item_id: UUID, image_id: UUID | None) -> UUID | None:
    if image_id is None:
        return None
    async with AsyncSessionLocal() as db:
        from app.services.ai_service import detect_image

        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return None
        job = await db.get(ScanJob, item.scan_job_id)
        detection = await detect_image(db, image_id, verification=bool(job and job.job_type == "auto_verify"))
        return detection.id


async def _load_all_tanks(db: AsyncSession, shelf_id: UUID | None = None) -> list[Tank]:
    stmt = select(Tank).order_by(Tank.level_index, Tank.row_index, Tank.col_index, Tank.code)
    if shelf_id is not None:
        stmt = stmt.where(Tank.shelf_id == shelf_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _load_tanks_for_schedule(db: AsyncSession, schedule: ScanSchedule) -> list[Tank]:
    if schedule.scan_mode in {"all_tanks", "single_shelf"}:
        return await _load_all_tanks(db, shelf_id=schedule.shelf_id)

    if schedule.scan_mode in {"selected_tanks", "single_tank"}:
        tank_ids = [UUID(tank_id) for tank_id in schedule.tank_ids or []]
        result = await db.execute(
            select(Tank)
            .where(Tank.id.in_(tank_ids))
            .order_by(Tank.level_index, Tank.row_index, Tank.col_index, Tank.code)
        )
        return list(result.scalars().all())

    return []


def _filter_recently_scanned(tanks: list[Tank]) -> list[Tank]:
    if settings.scan_dedupe_seconds <= 0:
        return tanks
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.scan_dedupe_seconds)
    return [tank for tank in tanks if tank.last_checked_at is None or tank.last_checked_at < cutoff]


def _final_job_status(statuses: list[str], is_simulation: bool) -> str:
    if not statuses:
        return "success"
    if all(status == "simulated" for status in statuses) or (is_simulation and not any(status in {"failed", "timeout"} for status in statuses)):
        return "simulated"
    success_count = statuses.count("success")
    failed_count = len([status for status in statuses if status in {"failed", "timeout"}])
    if failed_count and success_count:
        return "partial_success"
    if failed_count and not success_count:
        return "failed"
    return "success"


async def _set_item_status(item_id: UUID, item_status: str, *, started: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = item_status
        if started:
            item.started_at = datetime.now(timezone.utc)
        await db.commit()
        await _broadcast_item(item)


async def _finish_item(item_id: UUID, item_status: str, message: str | None = None) -> None:
    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = item_status
        item.error_message = message
        item.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await _broadcast_item(item)


async def _broadcast_item(item: ScanJobItem) -> None:
    await realtime_service.broadcast(
        "scan_job_item_updated",
        {
            "id": str(item.id),
            "scan_job_id": str(item.scan_job_id),
            "tank_id": str(item.tank_id),
            "status": item.status,
            "image_id": str(item.image_id) if item.image_id else None,
            "detection_id": str(item.detection_id) if item.detection_id else None,
            "error_message": item.error_message,
        },
    )
