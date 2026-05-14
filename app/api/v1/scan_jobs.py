from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.scan import ScanJobRead
from app.services import scan_service

router = APIRouter()


@router.get("", response_model=list[ScanJobRead])
async def list_scan_jobs(db: AsyncSession = Depends(get_db)):
    return await scan_service.list_scan_jobs(db)


@router.get("/{job_id}", response_model=ScanJobRead)
async def get_scan_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_service.get_scan_job(db, job_id)
