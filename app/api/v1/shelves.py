from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.shelf import ShelfCreate, ShelfRead, ShelfUpdate
from app.services import shelf_service

router = APIRouter()


@router.get("", response_model=list[ShelfRead])
async def list_shelves(db: AsyncSession = Depends(get_db)):
    return await shelf_service.list_shelves(db)


@router.post("", response_model=ShelfRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("admin"))])
async def create_shelf(data: ShelfCreate, db: AsyncSession = Depends(get_db)):
    return await shelf_service.create_shelf(db, data)


@router.get("/{shelf_id}", response_model=ShelfRead)
async def get_shelf(shelf_id: UUID, db: AsyncSession = Depends(get_db)):
    return await shelf_service.get_shelf(db, shelf_id)


@router.patch("/{shelf_id}", response_model=ShelfRead, dependencies=[Depends(require_roles("admin"))])
async def update_shelf(shelf_id: UUID, data: ShelfUpdate, db: AsyncSession = Depends(get_db)):
    return await shelf_service.update_shelf(db, shelf_id, data)


@router.post("/{shelf_id}/maintenance", response_model=ShelfRead, dependencies=[Depends(require_roles("admin", "operator"))])
async def set_maintenance(shelf_id: UUID, db: AsyncSession = Depends(get_db)):
    return await shelf_service.set_shelf_status(db, shelf_id, "maintenance")


@router.post("/{shelf_id}/activate", response_model=ShelfRead, dependencies=[Depends(require_roles("admin", "operator"))])
async def activate(shelf_id: UUID, db: AsyncSession = Depends(get_db)):
    return await shelf_service.set_shelf_status(db, shelf_id, "active")
