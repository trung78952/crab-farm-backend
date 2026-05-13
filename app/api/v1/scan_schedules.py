from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.scan import ScanScheduleCreate, ScanScheduleRead, ScanScheduleUpdate
from app.services import scan_schedule_service

router = APIRouter()


@router.get("", response_model=list[ScanScheduleRead], dependencies=[Depends(require_roles("operator"))])
async def list_scan_schedules(db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.list_scan_schedules(db)


@router.post("", response_model=ScanScheduleRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def create_scan_schedule(data: ScanScheduleCreate, db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.create_scan_schedule(db, data)


@router.get("/{schedule_id}", response_model=ScanScheduleRead, dependencies=[Depends(require_roles("operator"))])
async def get_scan_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.get_scan_schedule(db, schedule_id)


@router.patch("/{schedule_id}", response_model=ScanScheduleRead, dependencies=[Depends(require_roles("operator"))])
async def update_scan_schedule(schedule_id: UUID, data: ScanScheduleUpdate, db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.update_scan_schedule(db, schedule_id, data)


@router.post("/{schedule_id}/enable", response_model=ScanScheduleRead, dependencies=[Depends(require_roles("operator"))])
async def enable_scan_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.enable_scan_schedule(db, schedule_id)


@router.post("/{schedule_id}/disable", response_model=ScanScheduleRead, dependencies=[Depends(require_roles("operator"))])
async def disable_scan_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_schedule_service.disable_scan_schedule(db, schedule_id)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles("operator"))])
async def delete_scan_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)):
    await scan_schedule_service.delete_scan_schedule(db, schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
