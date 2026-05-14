from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.schemas.training_sample import DatasetExportRead, TrainingSampleLabelRequest, TrainingSampleRead
from app.services import dataset_service

router = APIRouter()


@router.get("", response_model=list[TrainingSampleRead])
async def list_samples(verified: bool | None = None, db: AsyncSession = Depends(get_db)):
    return await dataset_service.list_samples(db, verified=verified)


@router.post("/from-detection/{detection_id}", response_model=TrainingSampleRead, dependencies=[Depends(require_roles("operator"))])
async def from_detection(detection_id: UUID, db: AsyncSession = Depends(get_db)):
    return await dataset_service.create_from_detection(db, detection_id)


@router.patch("/{sample_id}/label", response_model=TrainingSampleRead, dependencies=[Depends(require_roles("operator"))])
async def label_sample(
    sample_id: UUID,
    data: TrainingSampleLabelRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await dataset_service.label_sample(db, sample_id, data, current_user.id)


@router.post("/export-yolo", response_model=DatasetExportRead, dependencies=[Depends(require_roles("operator"))])
async def export_yolo(db: AsyncSession = Depends(get_db)):
    return await dataset_service.export_yolo_dataset(db)
