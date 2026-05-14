from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.recheck_task import RecheckTask
from app.schemas.recheck_task import RecheckTaskCreate
from app.services.realtime_service import realtime_service


async def list_recheck_tasks(db: AsyncSession) -> list[RecheckTask]:
    result = await db.execute(select(RecheckTask).order_by(RecheckTask.run_at.desc()))
    return list(result.scalars().all())


async def create_recheck_task(db: AsyncSession, data: RecheckTaskCreate) -> RecheckTask:
    task = RecheckTask(**data.model_dump(), status="scheduled")
    db.add(task)
    await db.flush()
    await realtime_service.broadcast(
        "harvest_updated",
        {"recheck_task_id": str(task.id), "tank_id": str(task.tank_id), "reason": task.reason, "status": task.status},
    )
    return task


async def cancel_recheck_task(db: AsyncSession, task_id: UUID) -> RecheckTask:
    task = await db.get(RecheckTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recheck task not found")
    task.status = "cancelled"
    await db.commit()
    await db.refresh(task)
    await realtime_service.broadcast("harvest_updated", {"recheck_task_id": str(task.id), "status": task.status})
    return task


async def run_due_recheck_tasks_now() -> int:
    from app.services.scan_service import create_recheck_scan_job

    count = 0
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RecheckTask)
            .where(RecheckTask.status == "scheduled", RecheckTask.run_at <= now)
            .order_by(RecheckTask.priority, RecheckTask.run_at)
        )
        tasks = list(result.scalars().all())
        for task in tasks:
            await create_recheck_scan_job(db, task)
            task.status = "queued"
            count += 1
        await db.commit()
    return count
