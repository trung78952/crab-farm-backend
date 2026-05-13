from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.tank import TankCreate, TankRead, TankUpdate
from app.services import tank_service

router = APIRouter()


@router.get("", response_model=list[TankRead])
async def list_tanks(db: AsyncSession = Depends(get_db)):
    return await tank_service.list_tanks(db)


@router.post("", response_model=TankRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin"))])
async def create_tank(data: TankCreate, db: AsyncSession = Depends(get_db)):
    return await tank_service.create_tank(db, data)


@router.get("/{tank_id}", response_model=TankRead)
async def get_tank(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    return await tank_service.get_tank(db, tank_id)


@router.patch("/{tank_id}", response_model=TankRead, dependencies=[Depends(require_roles("admin"))])
async def update_tank(tank_id: UUID, data: TankUpdate, db: AsyncSession = Depends(get_db)):
    return await tank_service.update_tank(db, tank_id, data)


@router.delete("/{tank_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("admin"))])
async def delete_tank(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    await tank_service.delete_tank(db, tank_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
