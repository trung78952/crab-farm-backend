from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.shelf import Shelf
from app.schemas.device import DeviceCreate, DeviceStatusUpdate
from app.services.realtime_service import realtime_service


async def list_devices(db: AsyncSession) -> list[Device]:
    result = await db.execute(select(Device).order_by(Device.code))
    return list(result.scalars().all())


async def create_device(db: AsyncSession, data: DeviceCreate) -> Device:
    payload = data.model_dump()
    if payload.get("shelf_id") is not None and await db.get(Shelf, payload["shelf_id"]) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    metadata = payload.pop("metadata", {})
    device = Device(**payload, metadata_=metadata)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    await realtime_service.broadcast(
        "device_status_updated",
        {"id": str(device.id), "code": device.code, "status": device.status, "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None},
    )
    return device


async def update_device_status(db: AsyncSession, device_id: UUID, data: DeviceStatusUpdate) -> Device:
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    device.status = data.status
    device.last_seen_at = data.last_seen_at or datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    await realtime_service.broadcast(
        "device_status_updated",
        {"id": str(device.id), "code": device.code, "status": device.status, "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None},
    )
    return device
