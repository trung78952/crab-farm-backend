from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.scan_schedule import ScanSchedule
from app.services.scan_schedule_service import mark_schedule_dispatched
from app.services.scan_service import create_scan_job_from_schedule
from app.services.recheck_task_service import run_due_recheck_tasks_now

logger = logging.getLogger(__name__)


class ScanScheduler:
    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                await dispatch_due_scan_schedules()
            except Exception:
                logger.exception("Failed to dispatch due scan schedules")

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue


async def dispatch_due_scan_schedules() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ScanSchedule).where(
                ScanSchedule.is_active.is_(True),
                ScanSchedule.next_run_at.is_not(None),
                ScanSchedule.next_run_at <= now,
            )
        )
        schedules = list(result.scalars().all())

        for schedule in schedules:
            if schedule.start_time is not None and now < schedule.start_time:
                continue
            if schedule.end_time is not None and now > schedule.end_time:
                continue

            job = await create_scan_job_from_schedule(db, schedule)
            await mark_schedule_dispatched(db, schedule, now=now)
            await db.commit()
        await run_due_recheck_tasks_now()


scan_scheduler = ScanScheduler()
