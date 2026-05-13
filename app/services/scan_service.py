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
from app.models.scan_job import ScanJob
from app.models.scan_job_item import ScanJobItem
from app.models.scan_schedule import ScanSchedule
from app.models.tank import Tank
from app.services import camera_service, motion_service

logger = logging.getLogger(__name__)


async def run_all(db: AsyncSession) -> ScanJob:
    tanks = await _load_all_tanks(db)
    job = await create_scan_job(db, scan_mode="all_tanks", tanks=tanks)
    start_scan_job_background(job.id)
    return await get_scan_job(db, job.id)


async def run_tank(db: AsyncSession, tank_id: UUID) -> ScanJob:
    tank = await db.get(Tank, tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")

    job = await create_scan_job(db, scan_mode="single_tank", tanks=[tank])
    start_scan_job_background(job.id)
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
) -> ScanJob:
    job = ScanJob(
        schedule_id=schedule_id,
        status="queued",
        scan_mode=scan_mode,
        total_tanks=len(tanks),
        completed_tanks=0,
    )
    db.add(job)
    await db.flush()

    for tank in tanks:
        db.add(ScanJobItem(scan_job_id=job.id, tank_id=tank.id, status="queued"))

    await db.commit()
    return job


async def create_scan_job_from_schedule(db: AsyncSession, schedule: ScanSchedule) -> ScanJob:
    tanks = await _load_tanks_for_schedule(db, schedule)
    return await create_scan_job(db, scan_mode=schedule.scan_mode, tanks=tanks, schedule_id=schedule.id)


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
        job.status = "failed" if failed else "success"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def process_scan_job_item(item_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = "moving"
        item.started_at = datetime.now(timezone.utc)
        await db.commit()

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        await motion_service.move_to_tank(db, item.tank_id)

    await wait_for_motion_done_placeholder()

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.status = "capturing"
        await db.commit()
        await camera_service.capture_tank_image(db, item.tank_id)

    image_id = await wait_for_camera_result_placeholder(item_id)

    async with AsyncSessionLocal() as db:
        item = await db.get(ScanJobItem, item_id)
        if item is None:
            return
        item.image_id = image_id
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
        item.status = "success"
        item.completed_at = datetime.now(timezone.utc)
        await db.commit()


async def wait_for_motion_done_placeholder() -> None:
    await asyncio.sleep(0)


async def wait_for_camera_result_placeholder(item_id: UUID) -> UUID | None:
    await asyncio.sleep(0)
    return None


async def run_detection_placeholder(item_id: UUID, image_id: UUID | None) -> UUID | None:
    await asyncio.sleep(0)
    return None


async def _load_all_tanks(db: AsyncSession) -> list[Tank]:
    result = await db.execute(select(Tank).order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code))
    return list(result.scalars().all())


async def _load_tanks_for_schedule(db: AsyncSession, schedule: ScanSchedule) -> list[Tank]:
    if schedule.scan_mode == "all_tanks":
        return await _load_all_tanks(db)

    if schedule.scan_mode == "selected_tanks":
        tank_ids = [UUID(tank_id) for tank_id in schedule.tank_ids or []]
        result = await db.execute(
            select(Tank)
            .where(Tank.id.in_(tank_ids))
            .order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code)
        )
        return list(result.scalars().all())

    return []
