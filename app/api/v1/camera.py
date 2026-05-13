from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.image import CameraCaptureResponse, CameraUploadResponse, ImageRead
from app.services import camera_service

router = APIRouter()


@router.post("/capture/{tank_id}", response_model=CameraCaptureResponse, dependencies=[Depends(require_roles("operator"))])
async def capture(tank_id: UUID, db: AsyncSession = Depends(get_db)):
    return await camera_service.capture_tank_image(db, tank_id)


@router.post("/upload", response_model=CameraUploadResponse, dependencies=[Depends(require_roles("operator"))])
async def upload(
    tank_id: UUID = Form(...),
    device_id: UUID | None = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    image = await camera_service.upload_image(db, tank_id=tank_id, device_id=device_id, file=file)
    return {"image_id": image.id, "image_url": image.image_url}


@router.get("/images", response_model=list[ImageRead])
async def list_images(tank_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    return await camera_service.list_images(db, tank_id=tank_id)
