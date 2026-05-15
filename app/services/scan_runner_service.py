from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.scan_job import ScanJob
from app.services.scan_service import process_scan_job

logger = logging.getLogger(__name__)


class ScanRunner:
    def __init__(self, interval_seconds: int = 5) -> None:
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._busy_shelves: set[str] = set()

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
                await self.dispatch_once()
            except Exception:
                logger.exception("Failed to dispatch queued scan jobs")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def dispatch_once(self) -> None:
        async with AsyncSessionLocal() as db:
            running_result = await db.execute(select(ScanJob).where(ScanJob.status == "running"))
            running_shelves = {str(job.shelf_id or "global") for job in running_result.scalars().all()}
            result = await db.execute(
                select(ScanJob)
                .where(ScanJob.status == "queued")
                .order_by(ScanJob.priority, ScanJob.created_at)
            )
            jobs = list(result.scalars().all())

        for job in jobs:
            shelf_key = str(job.shelf_id or "global")
            if shelf_key in self._busy_shelves or shelf_key in running_shelves:
                continue
            self._busy_shelves.add(shelf_key)
            task = asyncio.create_task(self._run_job(job.id, shelf_key))
            task.add_done_callback(lambda t, key=shelf_key: self._busy_shelves.discard(key))

    async def _run_job(self, job_id, shelf_key: str) -> None:
        await process_scan_job(job_id)


scan_runner = ScanRunner()
