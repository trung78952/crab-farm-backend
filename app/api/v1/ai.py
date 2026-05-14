from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.ai import AiModelActivateRequest, AiModelRead, AiStatusRead
from app.schemas.detection import DetectionRead
from app.services import ai_service, model_registry_service

router = APIRouter()


@router.get("/status", response_model=AiStatusRead)
async def status():
    return ai_service.ai_status()


@router.post("/detect/{image_id}", response_model=DetectionRead, dependencies=[Depends(require_roles("operator"))])
async def detect(image_id: UUID, db: AsyncSession = Depends(get_db)):
    return await ai_service.detect_image(db, image_id)


@router.get("/models", response_model=list[AiModelRead])
async def list_models(db: AsyncSession = Depends(get_db)):
    return await model_registry_service.list_models(db)


@router.post("/models/activate", response_model=AiModelRead, dependencies=[Depends(require_roles("admin"))])
async def activate_model(data: AiModelActivateRequest, db: AsyncSession = Depends(get_db)):
    return await model_registry_service.activate_model(db, data)
