from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.scan import ScanJobRead
from app.services import scan_service

router = APIRouter()


@router.post("/run-all", response_model=ScanJobRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def run_all(db: AsyncSession = Depends(get_db)):
    return await scan_service.run_all(db)


@router.post("/run-tank/{tank_id}", response_model=ScanJobRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def run_tank(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_service.run_tank(db, tank_id)


@router.get("/jobs", response_model=list[ScanJobRead])
async def list_scan_jobs(db: AsyncSession = Depends(get_db)):
    return await scan_service.list_scan_jobs(db)


@router.get("/jobs/{job_id}", response_model=ScanJobRead)
async def get_scan_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    return await scan_service.get_scan_job(db, job_id)
