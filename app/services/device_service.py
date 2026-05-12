from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.schemas.device import DeviceCreate, DeviceStatusUpdate


async def list_devices(db: AsyncSession) -> list[Device]:
    result = await db.execute(select(Device).order_by(Device.code))
    return list(result.scalars().all())


async def create_device(db: AsyncSession, data: DeviceCreate) -> Device:
    payload = data.model_dump()
    metadata = payload.pop("metadata", {})
    device = Device(**payload, metadata_=metadata)
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def update_device_status(db: AsyncSession, device_id: UUID, data: DeviceStatusUpdate) -> Device:
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    device.status = data.status
    device.last_seen_at = data.last_seen_at or datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(device)
    return device
