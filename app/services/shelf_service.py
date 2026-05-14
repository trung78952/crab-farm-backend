from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shelf import Shelf
from app.schemas.shelf import ShelfCreate, ShelfUpdate
from app.services.realtime_service import realtime_service


async def list_shelves(db: AsyncSession) -> list[Shelf]:
    result = await db.execute(select(Shelf).order_by(Shelf.code))
    return list(result.scalars().all())


async def get_shelf(db: AsyncSession, shelf_id: UUID) -> Shelf:
    shelf = await db.get(Shelf, shelf_id)
    if shelf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    return shelf


async def create_shelf(db: AsyncSession, data: ShelfCreate) -> Shelf:
    payload = data.model_dump()
    metadata = payload.pop("metadata", {})
    shelf = Shelf(**payload, metadata_=metadata)
    db.add(shelf)
    await db.commit()
    await db.refresh(shelf)
    await realtime_service.broadcast("device_status_updated", {"shelf_id": str(shelf.id), "status": shelf.status})
    return shelf


async def update_shelf(db: AsyncSession, shelf_id: UUID, data: ShelfUpdate) -> Shelf:
    shelf = await get_shelf(db, shelf_id)
    payload = data.model_dump(exclude_unset=True)
    if "metadata" in payload:
        payload["metadata_"] = payload.pop("metadata") or {}
    for key, value in payload.items():
        setattr(shelf, key, value)
    await db.commit()
    await db.refresh(shelf)
    await realtime_service.broadcast("device_status_updated", {"shelf_id": str(shelf.id), "status": shelf.status})
    return shelf


async def set_shelf_status(db: AsyncSession, shelf_id: UUID, shelf_status: str) -> Shelf:
    return await update_shelf(db, shelf_id, ShelfUpdate(status=shelf_status))
