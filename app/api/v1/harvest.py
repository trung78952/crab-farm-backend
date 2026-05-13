from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.harvest import HarvestQueueRequest, HarvestRead
from app.services import harvest_service

router = APIRouter()


@router.post("/queue/{tank_id}", response_model=HarvestRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def queue_harvest(
    tank_id: UUID,
    data: HarvestQueueRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    note = data.note if data is not None else None
    return await harvest_service.queue_harvest(db, tank_id, note=note)


@router.post("/start/{harvest_id}", response_model=HarvestRead, dependencies=[Depends(require_roles("operator"))])
async def start_harvest(harvest_id: UUID, db: AsyncSession = Depends(get_db)):
    return await harvest_service.start_harvest(db, harvest_id)


@router.get("", response_model=list[HarvestRead])
async def list_harvests(db: AsyncSession = Depends(get_db)):
    return await harvest_service.list_harvests(db)
