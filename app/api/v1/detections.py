from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.schemas.detection import DetectionMockCreate, DetectionRead, DetectionVerifyRequest
from app.services import detection_service

router = APIRouter()


@router.post("/mock", response_model=DetectionRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("operator"))])
async def create_mock_detection(data: DetectionMockCreate, db: AsyncSession = Depends(get_db)):
    return await detection_service.create_mock_detection(db, data)


@router.get("", response_model=list[DetectionRead])
async def list_detections(db: AsyncSession = Depends(get_db)):
    return await detection_service.list_detections(db)


@router.get("/by-tank/{tank_id}", response_model=list[DetectionRead])
async def list_detections_by_tank(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    return await detection_service.list_detections_by_tank(db, tank_id)


@router.post("/{detection_id}/verify", response_model=DetectionRead, dependencies=[Depends(require_roles("operator"))])
async def verify_detection(
    detection_id: UUID,
    data: DetectionVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await detection_service.verify_detection(db, detection_id, data, current_user.id)
