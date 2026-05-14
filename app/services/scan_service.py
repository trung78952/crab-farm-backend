from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models.scan_job import ScanJob
from app.models.scan_job_item import ScanJobItem
from app.models.scan_schedule import ScanSchedule
from app.models.tank import Tank
from app.models.recheck_task import RecheckTask
from app.services import camera_service, motion_service
from app.services.realtime_service import realtime_service

logger = logging.getLogger(__name__)


async def run_all(db: AsyncSession) -> ScanJob:
    tanks = await _load_all_tanks(db)
    job = await create_scan_job(db, scan_mode="all_tanks", tanks=tanks, job_type="manual_scan")
    return await get_scan_job(db, job.id)


async def run_tank(db: AsyncSession, tank_id: UUID) -> ScanJob:
    tank = await db.get(Tank, tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")

    job = await create_scan_job(db, scan_mode="single_tank", tanks=[tank], job_type="manual_scan", shelf_id=tank.shelf_id)
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
    await realtime_service.broadcast("scan_job_created", {"id": str(job.id), "status": job.status, "shelf_id": str(job.shelf_id) if job.shelf_id else None})
    return job


async def create_scan_job_from_schedule(db: AsyncSession, schedule: ScanSchedule) -> ScanJob:
    tanks = await _load_tanks_for_schedule(db, schedule)
    return await create_scan_job(
        db,
        scan_mode="all_tanks" if schedule.scan_mode == "single_shelf" else schedule.scan_mode,
        tanks=tanks,
        schedule_id=schedule.id,
        shelf_id=schedule.shelf_id,
        job_type="scheduled_scan",
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
        job_type="recheck_scan" if task.reason != "suspected_soft_shell" else "verification_scan",
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

    failed = False
    for item in items:
        try:
            await process_scan_job_item(item.id)
        except Exception as exc:
            failed = True
            async with AsyncSessionLocal() as db:
                db_item = await db.get(ScanJobItem, item.id)
                if db_item is not None:
                    db_item.status = "failed"
                    db_item.error_message = str(exc)
                    db_item.completed_at = datetime.now(timezone.utc)
                    await db.commit()

    async with AsyncSessionLocal() as db:
        job = await db.get(ScanJob, job_id)
        if job is None:
            return

        result = await db.execute(
            select(ScanJobItem).where(
                ScanJobItem.scan_job_id == job_id,
                ScanJobItem.status == "success",
            )
        )
        job.completed_tanks = len(result.scalars().all())
        failed_count = await db.execute(
            select(ScanJobItem).where(
                ScanJobItem.scan_job_id == job_id,
                ScanJobItem.status.in_(["failed", "timeout"]),
            )
        )
        job.failed_tanks = len(failed_count.scalars().all())
        if settings.simulation_mode:
            job.status = "simulated"
        elif job.failed_tanks and job.completed_tanks:
            job.status = "partial_success"
        elif job.failed_tanks:
            job.status = "failed"
        else:
            job.status = "success"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await realtime_service.broadcast("scan_job_updated", {"id": str(job.id), "status": job.status})


async def process_scan_job_item(item_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = "moving"
        item.started_at = datetime.now(timezone.utc)
        await db.commit()
        await realtime_service.broadcast("scan_job_item_updated", {"id": str(item.id), "status": item.status})

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        command = await motion_service.move_to_tank(db, item.tank_id)
        item.motion_command_id = command.id
        if settings.simulation_mode:
            item.status = "simulated"
            item.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await realtime_service.broadcast("scan_job_item_updated", {"id": str(item.id), "status": item.status})
            return
        item.status = "waiting_for_motion"
        await db.commit()

    await wait_for_motion_done(command.id)

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = "motion_done"
        await db.commit()
        await asyncio.sleep(settings.motion_settle_ms / 1000)
        item.status = "capturing"
        await db.commit()
        camera_cmd = await camera_service.capture_tank_image(db, item.tank_id)
        item.camera_command_id = camera_cmd["cmd_id"]
        item.status = "waiting_for_camera"
        await db.commit()
        await realtime_service.broadcast("scan_job_item_updated", {"id": str(item.id), "status": item.status})

    image_id = await wait_for_camera_result_placeholder(item_id)

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.image_id = image_id
        if image_id is None:
            item.status = "timeout"
            item.error_message = "Camera result/image not received"
            await db.commit()
            return
        item.status = "detecting"
        await db.commit()

    detection_id = await run_detection_placeholder(item_id, image_id)

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
        await realtime_service.broadcast("scan_job_item_updated", {"id": str(item.id), "status": item.status})


async def wait_for_motion_done(command_id: UUID) -> None:
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


async def wait_for_camera_result_placeholder(item_id: UUID) -> UUID | None:
    deadline = datetime.now(timezone.utc).timestamp() + settings.camera_timeout_seconds
    while datetime.now(timezone.utc).timestamp() < deadline:
        async with AsyncSessionLocal() as db:
            item = await db.get(ScanJobItem, item_id)
            if item is not None and item.image_id is not None:
                return item.image_id
        await asyncio.sleep(0.5)
    return None


async def run_detection_placeholder(item_id: UUID, image_id: UUID | None) -> UUID | None:
    if image_id is None:
        return None
    async with AsyncSessionLocal() as db:
        from app.services.ai_service import detect_image

        detection = await detect_image(db, image_id)
        return detection.id


async def _load_all_tanks(db: AsyncSession) -> list[Tank]:
    result = await db.execute(select(Tank).order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code))
    return list(result.scalars().all())


async def _load_tanks_for_schedule(db: AsyncSession, schedule: ScanSchedule) -> list[Tank]:
    if schedule.scan_mode == "all_tanks":
        stmt = select(Tank).order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code)
        if schedule.shelf_id is not None:
            stmt = stmt.where(Tank.shelf_id == schedule.shelf_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    if schedule.scan_mode == "single_shelf":
        result = await db.execute(
            select(Tank)
            .where(Tank.shelf_id == schedule.shelf_id)
            .order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code)
        )
        return list(result.scalars().all())

    if schedule.scan_mode == "selected_tanks":
        tank_ids = [UUID(tank_id) for tank_id in schedule.tank_ids or []]
        result = await db.execute(
            select(Tank)
            .where(Tank.id.in_(tank_ids))
            .order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code)
        )
        return list(result.scalars().all())

    return []
