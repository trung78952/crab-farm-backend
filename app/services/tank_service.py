from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tank import Tank
from app.models.shelf import Shelf
from app.schemas.tank import TankCreate, TankUpdate
from app.services.realtime_service import realtime_service


async def list_tanks(db: AsyncSession, shelf_id: UUID | None = None) -> list[Tank]:
    stmt = select(Tank).order_by(Tank.level_index, Tank.row_index, Tank.col_index, Tank.code)
    if shelf_id is not None:
        stmt = stmt.where(Tank.shelf_id == shelf_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_tank(db: AsyncSession, tank_id: UUID) -> Tank:
    tank = await db.get(Tank, tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")
    return tank


async def create_tank(db: AsyncSession, data: TankCreate) -> Tank:
    if data.shelf_id is not None and await db.get(Shelf, data.shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    tank = Tank(**data.model_dump())
    db.add(tank)
    await db.commit()
    await db.refresh(tank)
    await realtime_service.broadcast(
        "tank_created",
        {"id": str(tank.id), "shelf_id": str(tank.shelf_id) if tank.shelf_id else None, "code": tank.code, "status": tank.status},
    )
    return tank


async def update_tank(db: AsyncSession, tank_id: UUID, data: TankUpdate) -> Tank:
    tank = await get_tank(db, tank_id)
    payload = data.model_dump(exclude_unset=True)
    if payload.get("shelf_id") is not None and await db.get(Shelf, payload["shelf_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    for key, value in payload.items():
        setattr(tank, key, value)
    await db.commit()
    await db.refresh(tank)
    await realtime_service.broadcast(
        "tank_updated",
        {"id": str(tank.id), "shelf_id": str(tank.shelf_id) if tank.shelf_id else None, "code": tank.code, "status": tank.status},
    )
    return tank


async def delete_tank(db: AsyncSession, tank_id: UUID) -> None:
    tank = await get_tank(db, tank_id)
    await db.delete(tank)
    await db.commit()
    await realtime_service.broadcast("tank_updated", {"id": str(tank_id), "deleted": True})
