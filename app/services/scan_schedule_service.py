from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan_schedule import ScanSchedule
from app.models.shelf import Shelf
from app.models.tank import Tank
from app.schemas.scan import ScanScheduleCreate, ScanScheduleUpdate
from app.services.realtime_service import realtime_service


async def list_scan_schedules(
    db: AsyncSession,
    *,
    shelf_id: UUID | None = None,
    tag: str | None = None,
    schedule_type: str | None = None,
    is_active: bool | None = None,
) -> list[ScanSchedule]:
    stmt = select(ScanSchedule).order_by(ScanSchedule.created_at.desc())
    if shelf_id is not None:
        stmt = stmt.where(ScanSchedule.shelf_id == shelf_id)
    if tag:
        stmt = stmt.where(ScanSchedule.tag == tag)
    if schedule_type:
        stmt = stmt.where(ScanSchedule.schedule_type == schedule_type)
    if is_active is not None:
        stmt = stmt.where(ScanSchedule.is_active.is_(is_active))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await db.get(ScanSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan schedule not found")
    return schedule


async def create_scan_schedule(db: AsyncSession, data: ScanScheduleCreate) -> ScanSchedule:
    payload = data.model_dump(exclude={"run_immediately"})
    await _validate_schedule_payload(db, payload)
    _normalize_schedule_payload(payload)
    _set_initial_next_run(payload, run_immediately=data.run_immediately)
    schedule = ScanSchedule(**payload)
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    await realtime_service.broadcast(
        "scan_schedule_created",
        {"id": str(schedule.id), "tag": schedule.tag, "schedule_type": schedule.schedule_type, "next_run_at": _iso(schedule.next_run_at)},
    )

    if data.run_immediately:
        from app.services.scan_service import create_scan_job_from_schedule

        await create_scan_job_from_schedule(db, schedule)
    return schedule


async def update_scan_schedule(db: AsyncSession, schedule_id: UUID, data: ScanScheduleUpdate) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    if schedule.tag == "AUTO" and schedule.created_by_system:
        mutable = {"is_active", "next_run_at", "expires_at", "max_runs"}
        requested = set(data.model_dump(exclude_unset=True).keys())
        if requested - mutable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AUTO schedules can only be enabled/disabled, cancelled, or lightly retimed")

    payload = data.model_dump(exclude_unset=True)
    merged = {
        "shelf_id": schedule.shelf_id,
        "schedule_type": schedule.schedule_type,
        "tag": schedule.tag,
        "scan_mode": schedule.scan_mode,
        "tank_ids": schedule.tank_ids,
        "interval_minutes": schedule.interval_minutes,
        **payload,
    }
    await _validate_schedule_payload(db, merged)
    if "tank_ids" in payload:
        payload["tank_ids"] = _dump_tank_ids(payload.get("tank_ids"))
    for key, value in payload.items():
        setattr(schedule, key, value)

    if schedule.schedule_type == "user_periodic":
        schedule.tag = "USER"
    elif schedule.tag == "USER":
        schedule.tag = "AUTO"

    await db.commit()
    await db.refresh(schedule)
    await realtime_service.broadcast(
        "scan_schedule_updated",
        {"id": str(schedule.id), "is_active": schedule.is_active, "next_run_at": _iso(schedule.next_run_at)},
    )
    return schedule


async def enable_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    schedule.is_active = True
    if schedule.next_run_at is None:
        schedule.next_run_at = _next_from_interval(schedule.interval_minutes)
    await db.commit()
    await db.refresh(schedule)
    await realtime_service.broadcast("scan_schedule_updated", {"id": str(schedule.id), "is_active": schedule.is_active})
    return schedule


async def disable_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    schedule.is_active = False
    await db.commit()
    await db.refresh(schedule)
    await realtime_service.broadcast("scan_schedule_updated", {"id": str(schedule.id), "is_active": schedule.is_active})
    return schedule


async def cancel_scan_schedule(db: AsyncSession, schedule_id: UUID) -> ScanSchedule:
    schedule = await get_scan_schedule(db, schedule_id)
    schedule.is_active = False
    schedule.completed_at = datetime.now(timezone.utc)
    schedule.stop_condition = schedule.stop_condition or "cancelled"
    await db.commit()
    await db.refresh(schedule)
    await realtime_service.broadcast("scan_schedule_updated", {"id": str(schedule.id), "is_active": schedule.is_active, "completed_at": _iso(schedule.completed_at)})
    return schedule


async def delete_scan_schedule(db: AsyncSession, schedule_id: UUID) -> None:
    schedule = await get_scan_schedule(db, schedule_id)
    await db.delete(schedule)
    await db.commit()


async def mark_schedule_dispatched(db: AsyncSession, schedule: ScanSchedule, now: datetime | None = None) -> None:
    run_at = now or datetime.now(timezone.utc)
    schedule.last_run_at = run_at
    schedule.run_count = (schedule.run_count or 0) + 1

    if schedule.run_once or (schedule.max_runs is not None and schedule.run_count >= schedule.max_runs):
        schedule.is_active = False
        schedule.completed_at = run_at
        schedule.next_run_at = None
        if schedule.max_runs is not None and schedule.run_count >= schedule.max_runs:
            schedule.stop_condition = "max_runs_reached"
        return

    if schedule.interval_minutes:
        schedule.next_run_at = run_at + timedelta(minutes=schedule.interval_minutes)
    else:
        schedule.is_active = False
        schedule.completed_at = run_at
        schedule.next_run_at = None


async def find_active_auto_schedule(
    db: AsyncSession,
    *,
    tank_id: UUID,
    schedule_type: str,
    auto_reason: str | None = None,
) -> ScanSchedule | None:
    tank_id_text = str(tank_id)
    result = await db.execute(
        select(ScanSchedule)
        .where(
            ScanSchedule.is_active.is_(True),
            ScanSchedule.tag == "AUTO",
            ScanSchedule.schedule_type == schedule_type,
            ScanSchedule.tank_ids.contains([tank_id_text]),
        )
        .order_by(ScanSchedule.created_at.desc())
    )
    schedules = list(result.scalars().all())
    if auto_reason:
        schedules = [schedule for schedule in schedules if schedule.auto_reason == auto_reason]
    return schedules[0] if schedules else None


async def complete_auto_schedules_for_tank(
    db: AsyncSession,
    *,
    tank_id: UUID,
    schedule_types: set[str] | None = None,
    stop_condition: str | None = None,
) -> int:
    tank_id_text = str(tank_id)
    result = await db.execute(
        select(ScanSchedule).where(
            ScanSchedule.is_active.is_(True),
            ScanSchedule.tag == "AUTO",
            ScanSchedule.tank_ids.contains([tank_id_text]),
        )
    )
    schedules = list(result.scalars().all())
    count = 0
    now = datetime.now(timezone.utc)
    for schedule in schedules:
        if schedule_types and schedule.schedule_type not in schedule_types:
            continue
        schedule.is_active = False
        schedule.completed_at = now
        if stop_condition:
            schedule.stop_condition = stop_condition
        count += 1
        await realtime_service.broadcast(
            "scan_schedule_updated",
            {"id": str(schedule.id), "is_active": schedule.is_active, "completed_at": schedule.completed_at.isoformat(), "stop_condition": schedule.stop_condition},
        )
    return count


def _normalize_schedule_payload(payload: dict) -> None:
    if payload.get("schedule_type") == "user_periodic":
        payload["tag"] = "USER"
        payload.setdefault("priority", 100)
    elif payload.get("tag") == "USER":
        payload["tag"] = "AUTO"
    if payload.get("scan_mode") == "single_shelf":
        payload["scan_mode"] = "all_tanks"
    payload["tank_ids"] = _dump_tank_ids(payload.get("tank_ids"))


def _set_initial_next_run(payload: dict, *, run_immediately: bool) -> None:
    if payload.get("next_run_at") is not None:
        return
    interval = payload.get("interval_minutes")
    if interval:
        payload["next_run_at"] = _next_from_interval(int(interval))
        return
    if run_immediately:
        payload["next_run_at"] = datetime.now(timezone.utc)


async def _validate_schedule_payload(db: AsyncSession, payload: dict) -> None:
    schedule_type = payload.get("schedule_type") or "user_periodic"
    scan_mode = payload.get("scan_mode") or "all_tanks"
    interval = payload.get("interval_minutes")
    tank_ids = payload.get("tank_ids")
    shelf_id = payload.get("shelf_id")

    if schedule_type in {"user_periodic", "auto_recheck"} and not interval:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="interval_minutes is required")
    if scan_mode == "selected_tanks" and not tank_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tank_ids is required when scan_mode is selected_tanks")
    if scan_mode == "single_tank" and len(tank_ids or []) != 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="single_tank schedules require exactly one tank_id")
    if scan_mode == "single_shelf" and shelf_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="shelf_id is required when scan_mode is single_shelf")

    await _validate_shelf_id(db, UUID(str(shelf_id)) if shelf_id else None)
    tanks = await _validate_tank_ids(db, [UUID(str(tank_id)) for tank_id in tank_ids or []])
    if tanks:
        tank_shelf_ids = {tank.shelf_id for tank in tanks}
        if len(tank_shelf_ids) > 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected tanks must belong to the same shelf")
        if shelf_id is not None and any(tank.shelf_id != UUID(str(shelf_id)) for tank in tanks):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected tanks must belong to shelf_id")


async def _validate_tank_ids(db: AsyncSession, tank_ids: list[UUID] | None) -> list[Tank]:
    if not tank_ids:
        return []

    result = await db.execute(select(Tank).where(Tank.id.in_(tank_ids)))
    tanks = list(result.scalars().all())
    existing_ids = {tank.id for tank in tanks}
    missing_ids = [str(tank_id) for tank_id in tank_ids if tank_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Some tanks do not exist", "tank_ids": missing_ids},
        )
    return tanks


async def _validate_shelf_id(db: AsyncSession, shelf_id: UUID | None) -> None:
    if shelf_id is None:
        return
    if await db.get(Shelf, shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")


def _dump_tank_ids(tank_ids: list[UUID | str] | None) -> list[str] | None:
    if tank_ids is None:
        return None
    return [str(tank_id) for tank_id in tank_ids]


def _next_from_interval(interval_minutes: int | None) -> datetime | None:
    if not interval_minutes:
        return None
    return datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
