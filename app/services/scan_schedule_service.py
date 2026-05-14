from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan_schedule import ScanSchedule
from app.models.shelf import Shelf
from app.models.tank import Tank
from app.schemas.scan import ScanScheduleCreate, ScanScheduleUpdate


async def list_scan_schedules(db: AsyncSession) -> list[ScanSchedule]:
    result = await db.execute(select(ScanSchedule).order_by(ScanSchedule.created_at.desc()))
    return list(result.scalars().all())


async def get_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await db.get(ScanSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan schedule not found")
    return schedule


async def create_scan_schedule(db: AsyncSession, data: ScanScheduleCreate) -> ScanSchedule:
    await _validate_shelf_id(db, data.shelf_id)
    await _validate_tank_ids(db, data.tank_ids)
    payload = data.model_dump()
    payload["tank_ids"] = _dump_tank_ids(data.tank_ids)
    if payload["next_run_at"] is None:
        payload["next_run_at"] = datetime.now(timezone.utc)

    schedule = ScanSchedule(**payload)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def update_scan_schedule(db: AsyncSession, schedule_id: UUID, data: ScanScheduleUpdate) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    payload = data.model_dump(exclude_unset=True)

    if "tank_ids" in payload:
        await _validate_tank_ids(db, data.tank_ids)
        payload["tank_ids"] = _dump_tank_ids(data.tank_ids)
    if "shelf_id" in payload:
        await _validate_shelf_id(db, data.shelf_id)

    for key, value in payload.items():
        setattr(schedule, key, value)

    if schedule.scan_mode == "selected_tanks" and not schedule.tank_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tank_ids is required when scan_mode is selected_tanks",
        )
    if schedule.scan_mode == "single_shelf" and schedule.shelf_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="shelf_id is required when scan_mode is single_shelf",
        )

    await db.commit()
    await db.refresh(schedule)
    return schedule


async def enable_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    schedule.is_active = True
    if schedule.next_run_at is None:
        schedule.next_run_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def disable_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    schedule.is_active = False
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def delete_scan_schedule(db: AsyncSession, schedule_id: UUID) -> None:
    schedule = await get_scan_schedule(db, schedule_id)
    await db.delete(schedule)
    await db.commit()


async def mark_schedule_dispatched(db: AsyncSession, schedule: ScanSchedule, now: datetime | None = None) -> None:
    run_at = now or datetime.now(timezone.utc)
    schedule.last_run_at = run_at
    schedule.next_run_at = run_at + timedelta(minutes=schedule.interval_minutes)
    await db.flush()


async def _validate_tank_ids(db: AsyncSession, tank_ids: list[UUID] | None) -> None:
    if not tank_ids:
        return

    result = await db.execute(select(Tank.id).where(Tank.id.in_(tank_ids)))
    existing_ids = set(result.scalars().all())
    missing_ids = [str(tank_id) for tank_id in tank_ids if tank_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Some tanks do not exist", "tank_ids": missing_ids},
        )


async def _validate_shelf_id(db: AsyncSession, shelf_id: UUID | None) -> None:
    if shelf_id is None:
        return
    if await db.get(Shelf, shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")


def _dump_tank_ids(tank_ids: list[UUID] | None) -> list[str] | None:
    if tank_ids is None:
        return None
    return [str(tank_id) for tank_id in tank_ids]
