from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.harvest import Harvest
from app.services.motion_service import create_harvest_motion_command
from app.services.tank_service import get_tank


async def queue_harvest(db: AsyncSession, tank_id: UUID, note: str | None = None) -> Harvest:
    tank = await get_tank(db, tank_id)
    harvest = Harvest(tank_id=tank.id, status="queued", note=note)
    db.add(harvest)
    await db.commit()
    await db.refresh(harvest)
    return harvest


async def start_harvest(db: AsyncSession, harvest_id: UUID) -> Harvest:
    harvest = await db.get(Harvest, harvest_id)
    if harvest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Harvest not found")
    if harvest.status not in {"queued", "failed"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Harvest is not startable")

    command = await create_harvest_motion_command(db, harvest.tank_id, harvest.id)
    harvest.motion_command_id = command.id
    harvest.status = "running"
    await db.commit()
    await db.refresh(harvest)
    return harvest


async def list_harvests(db: AsyncSession) -> list[Harvest]:
    result = await db.execute(select(Harvest).order_by(Harvest.created_at.desc()))
    return list(result.scalars().all())


async def complete_harvest(db: AsyncSession, harvest: Harvest, success: bool, note: str | None = None) -> Harvest:
    harvest.status = "success" if success else "failed"
    harvest.completed_at = datetime.now(timezone.utc)
    if note:
        harvest.note = note
    await db.commit()
    await db.refresh(harvest)
    return harvest
