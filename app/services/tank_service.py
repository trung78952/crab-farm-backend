from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tank import Tank
from app.schemas.tank import TankCreate, TankUpdate


async def list_tanks(db: AsyncSession) -> list[Tank]:
    result = await db.execute(select(Tank).order_by(Tank.row_index, Tank.col_index, Tank.level_index, Tank.code))
    return list(result.scalars().all())


async def get_tank(db: AsyncSession, tank_id: UUID) -> Tank:
    tank = await db.get(Tank, tank_id)
    if tank is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")
    return tank


async def create_tank(db: AsyncSession, data: TankCreate) -> Tank:
    tank = Tank(**data.model_dump())
    db.add(tank)
    await db.commit()
    await db.refresh(tank)
    return tank


async def update_tank(db: AsyncSession, tank_id: UUID, data: TankUpdate) -> Tank:
    tank = await get_tank(db, tank_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tank, key, value)
    await db.commit()
    await db.refresh(tank)
    return tank


async def delete_tank(db: AsyncSession, tank_id: UUID) -> None:
    tank = await get_tank(db, tank_id)
    await db.delete(tank)
    await db.commit()
