from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.recheck_task import RecheckTaskRead
from app.services import recheck_task_service

router = APIRouter()


@router.get("", response_model=list[RecheckTaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    return await recheck_task_service.list_recheck_tasks(db)


@router.post("/{task_id}/cancel", response_model=RecheckTaskRead, dependencies=[Depends(require_roles("operator"))])
async def cancel(task_id: UUID, db: AsyncSession = Depends(get_db)):
    return await recheck_task_service.cancel_recheck_task(db, task_id)


@router.post("/run-due-now", dependencies=[Depends(require_roles("operator"))])
async def run_due_now():
    count = await recheck_task_service.run_due_recheck_tasks_now()
    return {"queued": count}
