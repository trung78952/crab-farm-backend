from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.sensor import Sensor, SensorAlert, SensorAlertRule, SensorReading, SensorType
from app.models.shelf import Shelf
from app.models.tank import Tank
from app.schemas.sensor import (
    SensorAlertRuleCreate,
    SensorAlertRuleUpdate,
    SensorCreate,
    SensorReadingCreate,
    SensorTypeCreate,
    SensorTypeUpdate,
    SensorUpdate,
)
from app.services.realtime_service import realtime_service


async def list_sensor_types(db: AsyncSession) -> list[SensorType]:
    result = await db.execute(select(SensorType).order_by(SensorType.code))
    return list(result.scalars().all())


async def get_sensor_type(db: AsyncSession, sensor_type_id: UUID) -> SensorType:
    sensor_type = await db.get(SensorType, sensor_type_id)
    if sensor_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor type not found")
    return sensor_type


async def get_sensor_type_by_code(db: AsyncSession, code: str) -> SensorType | None:
    result = await db.execute(select(SensorType).where(SensorType.code == code))
    return result.scalar_one_or_none()


async def create_sensor_type(db: AsyncSession, data: SensorTypeCreate) -> SensorType:
    payload = data.model_dump()
    metadata = payload.pop("metadata", None)
    sensor_type = SensorType(**payload, metadata_=metadata)
    db.add(sensor_type)
    await db.commit()
    await db.refresh(sensor_type)
    return sensor_type


async def update_sensor_type(db: AsyncSession, sensor_type_id: UUID, data: SensorTypeUpdate) -> SensorType:
    sensor_type = await get_sensor_type(db, sensor_type_id)
    payload = data.model_dump(exclude_unset=True)
    if "metadata" in payload:
        payload["metadata_"] = payload.pop("metadata")
    for key, value in payload.items():
        setattr(sensor_type, key, value)
    await db.commit()
    await db.refresh(sensor_type)
    return sensor_type


async def list_sensors(
    db: AsyncSession,
    *,
    shelf_id: UUID | None = None,
    tank_id: UUID | None = None,
    sensor_type: str | None = None,
) -> list[Sensor]:
    stmt = select(Sensor).join(SensorType).order_by(Sensor.code)
    if shelf_id is not None:
        stmt = stmt.where(Sensor.shelf_id == shelf_id)
    if tank_id is not None:
        stmt = stmt.where(Sensor.tank_id == tank_id)
    if sensor_type:
        stmt = stmt.where(SensorType.code == sensor_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_sensor(db: AsyncSession, sensor_id: UUID) -> Sensor:
    sensor = await db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


async def get_sensor_by_code(db: AsyncSession, sensor_code: str) -> Sensor | None:
    result = await db.execute(select(Sensor).where(Sensor.code == sensor_code))
    return result.scalar_one_or_none()


async def create_sensor(db: AsyncSession, data: SensorCreate) -> Sensor:
    await _validate_sensor_refs(
        db,
        sensor_type_id=data.sensor_type_id,
        shelf_id=data.shelf_id,
        tank_id=data.tank_id,
        device_id=data.device_id,
    )
    payload = data.model_dump()
    metadata = payload.pop("metadata", None)
    sensor = Sensor(**payload, metadata_=metadata)
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    await realtime_service.broadcast(
        "sensor_updated",
        {"id": str(sensor.id), "code": sensor.code, "status": sensor.status},
    )
    return sensor


async def update_sensor(db: AsyncSession, sensor_id: UUID, data: SensorUpdate) -> Sensor:
    sensor = await get_sensor(db, sensor_id)
    payload = data.model_dump(exclude_unset=True)
    if "metadata" in payload:
        payload["metadata_"] = payload.pop("metadata")

    await _validate_sensor_refs(
        db,
        sensor_type_id=payload.get("sensor_type_id"),
        shelf_id=payload.get("shelf_id") if "shelf_id" in payload else sensor.shelf_id,
        tank_id=payload.get("tank_id") if "tank_id" in payload else sensor.tank_id,
        device_id=payload.get("device_id") if "device_id" in payload else sensor.device_id,
    )

    for key, value in payload.items():
        setattr(sensor, key, value)
    if sensor.tank_id is None and sensor.shelf_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one of tank_id or shelf_id is required")
    await db.commit()
    await db.refresh(sensor)
    await realtime_service.broadcast(
        "sensor_updated",
        {"id": str(sensor.id), "code": sensor.code, "status": sensor.status},
    )
    return sensor


async def deactivate_sensor(db: AsyncSession, sensor_id: UUID) -> Sensor:
    sensor = await get_sensor(db, sensor_id)
    sensor.status = "inactive"
    await db.commit()
    await db.refresh(sensor)
    await realtime_service.broadcast("sensor_updated", {"id": str(sensor.id), "status": sensor.status})
    return sensor


async def list_sensor_readings(
    db: AsyncSession,
    *,
    sensor_id: UUID | None = None,
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    limit: int = 100,
) -> list[SensorReading]:
    stmt = select(SensorReading).order_by(SensorReading.measured_at.desc()).limit(limit)
    if sensor_id is not None:
        stmt = stmt.where(SensorReading.sensor_id == sensor_id)
    if tank_id is not None:
        stmt = stmt.where(SensorReading.tank_id == tank_id)
    if shelf_id is not None:
        stmt = stmt.where(SensorReading.shelf_id == shelf_id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.measured_at >= from_)
    if to is not None:
        stmt = stmt.where(SensorReading.measured_at <= to)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_sensor_reading(db: AsyncSession, data: SensorReadingCreate) -> SensorReading:
    sensor = await get_sensor(db, data.sensor_id)
    sensor_type = await get_sensor_type(db, sensor.sensor_type_id)
    tank_id = data.tank_id if data.tank_id is not None else sensor.tank_id
    shelf_id = data.shelf_id if data.shelf_id is not None else sensor.shelf_id

    if tank_id is None and shelf_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reading must belong to a tank or shelf")
    if tank_id is not None and await db.get(Tank, tank_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")
    if shelf_id is not None and await db.get(Shelf, shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")

    reading = SensorReading(
        sensor_id=sensor.id,
        tank_id=tank_id,
        shelf_id=shelf_id,
        value=data.value,
        unit=data.unit or sensor_type.unit,
        measured_at=data.measured_at or datetime.now(timezone.utc),
    )
    db.add(reading)
    await db.flush()
    alerts = await _create_alerts_for_reading(db, sensor, sensor_type, reading)
    await db.commit()
    await db.refresh(reading)

    await realtime_service.broadcast(
        "sensor_reading_created",
        {
            "id": str(reading.id),
            "sensor_id": str(reading.sensor_id),
            "tank_id": str(reading.tank_id) if reading.tank_id else None,
            "shelf_id": str(reading.shelf_id) if reading.shelf_id else None,
            "value": reading.value,
            "unit": reading.unit,
            "measured_at": reading.measured_at.isoformat(),
            "sensor_type": sensor_type.code,
        },
    )
    for alert in alerts:
        await realtime_service.broadcast(
            "sensor_alert_created",
            {
                "id": str(alert.id),
                "sensor_id": str(alert.sensor_id),
                "tank_id": str(alert.tank_id) if alert.tank_id else None,
                "shelf_id": str(alert.shelf_id) if alert.shelf_id else None,
                "alert_type": alert.alert_type,
                "message": alert.message,
                "status": alert.status,
            },
        )
    return reading


async def latest_sensor_readings(
    db: AsyncSession,
    *,
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
) -> list[SensorReading]:
    if tank_id is None and shelf_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tank_id or shelf_id is required")
    stmt = select(SensorReading).join(Sensor).order_by(SensorReading.measured_at.desc())
    if tank_id is not None:
        stmt = stmt.where(SensorReading.tank_id == tank_id)
    if shelf_id is not None:
        stmt = stmt.where(or_(SensorReading.shelf_id == shelf_id, Sensor.shelf_id == shelf_id))
    result = await db.execute(stmt.limit(500))
    readings = list(result.scalars().all())
    latest_by_sensor: dict[UUID, SensorReading] = {}
    for reading in readings:
        latest_by_sensor.setdefault(reading.sensor_id, reading)
    return list(latest_by_sensor.values())


async def list_sensor_alert_rules(db: AsyncSession) -> list[SensorAlertRule]:
    result = await db.execute(select(SensorAlertRule).order_by(SensorAlertRule.created_at.desc()))
    return list(result.scalars().all())


async def get_sensor_alert_rule(db: AsyncSession, rule_id: UUID) -> SensorAlertRule:
    rule = await db.get(SensorAlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor alert rule not found")
    return rule


async def create_sensor_alert_rule(db: AsyncSession, data: SensorAlertRuleCreate) -> SensorAlertRule:
    await _validate_rule_refs(db, data.sensor_type_id, data.shelf_id, data.tank_id)
    rule = SensorAlertRule(**data.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_sensor_alert_rule(db: AsyncSession, rule_id: UUID, data: SensorAlertRuleUpdate) -> SensorAlertRule:
    rule = await get_sensor_alert_rule(db, rule_id)
    payload = data.model_dump(exclude_unset=True)
    await _validate_rule_refs(
        db,
        payload.get("sensor_type_id", rule.sensor_type_id),
        payload.get("shelf_id", rule.shelf_id),
        payload.get("tank_id", rule.tank_id),
    )
    for key, value in payload.items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def list_sensor_alerts(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    tank_id: UUID | None = None,
    shelf_id: UUID | None = None,
) -> list[SensorAlert]:
    stmt = select(SensorAlert).order_by(SensorAlert.created_at.desc())
    if status_filter:
        stmt = stmt.where(SensorAlert.status == status_filter)
    if tank_id is not None:
        stmt = stmt.where(SensorAlert.tank_id == tank_id)
    if shelf_id is not None:
        stmt = stmt.where(SensorAlert.shelf_id == shelf_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_sensor_alert(db: AsyncSession, alert_id: UUID) -> SensorAlert:
    alert = await _get_alert(db, alert_id)
    alert.status = "acknowledged"
    await db.commit()
    await db.refresh(alert)
    await realtime_service.broadcast("sensor_alert_created", {"id": str(alert.id), "status": alert.status})
    return alert


async def resolve_sensor_alert(db: AsyncSession, alert_id: UUID) -> SensorAlert:
    alert = await _get_alert(db, alert_id)
    alert.status = "resolved"
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    await realtime_service.broadcast("sensor_alert_created", {"id": str(alert.id), "status": alert.status})
    return alert


async def create_sensor_reading_from_mqtt(db: AsyncSession, topic: str, payload: dict[str, Any]) -> SensorReading | None:
    sensor_code = payload.get("sensor_code")
    if not sensor_code:
        return None
    sensor = await get_sensor_by_code(db, str(sensor_code))
    if sensor is None:
        return None

    tank_id = sensor.tank_id
    shelf_id = sensor.shelf_id
    if payload.get("tank_code"):
        tank = await _get_tank_by_code(db, str(payload["tank_code"]))
        if tank is not None:
            tank_id = tank.id
            shelf_id = tank.shelf_id or shelf_id
    if payload.get("shelf_code"):
        shelf = await _get_shelf_by_code(db, str(payload["shelf_code"]))
        if shelf is not None:
            shelf_id = shelf.id

    measured_at = _parse_datetime(payload.get("measured_at"))
    return await create_sensor_reading(
        db,
        SensorReadingCreate(
            sensor_id=sensor.id,
            tank_id=tank_id,
            shelf_id=shelf_id,
            value=float(payload["value"]),
            unit=str(payload.get("unit") or ""),
            measured_at=measured_at,
        ),
    )


async def _create_alerts_for_reading(
    db: AsyncSession,
    sensor: Sensor,
    sensor_type: SensorType,
    reading: SensorReading,
) -> list[SensorAlert]:
    result = await db.execute(
        select(SensorAlertRule).where(
            SensorAlertRule.sensor_type_id == sensor_type.id,
            SensorAlertRule.is_active.is_(True),
            or_(SensorAlertRule.tank_id.is_(None), SensorAlertRule.tank_id == reading.tank_id),
            or_(SensorAlertRule.shelf_id.is_(None), SensorAlertRule.shelf_id == reading.shelf_id),
        )
    )
    rules = list(result.scalars().all())
    alerts: list[SensorAlert] = []
    for rule in rules:
        alert_type: str | None = None
        threshold: float | None = None
        if rule.min_value is not None and reading.value < rule.min_value:
            alert_type = "low"
            threshold = rule.min_value
        elif rule.max_value is not None and reading.value > rule.max_value:
            alert_type = "high"
            threshold = rule.max_value
        if alert_type is None:
            continue
        message = f"{sensor_type.name} {reading.value:g}{reading.unit} is {alert_type} threshold {threshold:g}{reading.unit}"
        alert = SensorAlert(
            sensor_id=sensor.id,
            reading_id=reading.id,
            tank_id=reading.tank_id,
            shelf_id=reading.shelf_id,
            alert_type=alert_type,
            message=message,
            status="open",
        )
        db.add(alert)
        await db.flush()
        alerts.append(alert)
    return alerts


async def _validate_sensor_refs(
    db: AsyncSession,
    *,
    sensor_type_id: UUID | None,
    shelf_id: UUID | None,
    tank_id: UUID | None,
    device_id: UUID | None,
) -> None:
    if sensor_type_id is not None and await db.get(SensorType, sensor_type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor type not found")
    if shelf_id is not None and await db.get(Shelf, shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    if tank_id is not None and await db.get(Tank, tank_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")
    if device_id is not None and await db.get(Device, device_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")


async def _validate_rule_refs(db: AsyncSession, sensor_type_id: UUID, shelf_id: UUID | None, tank_id: UUID | None) -> None:
    if await db.get(SensorType, sensor_type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor type not found")
    if shelf_id is not None and await db.get(Shelf, shelf_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shelf not found")
    if tank_id is not None and await db.get(Tank, tank_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tank not found")


async def _get_alert(db: AsyncSession, alert_id: UUID) -> SensorAlert:
    alert = await db.get(SensorAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor alert not found")
    return alert


async def _get_tank_by_code(db: AsyncSession, code: str) -> Tank | None:
    result = await db.execute(select(Tank).where(Tank.code == code))
    return result.scalar_one_or_none()


async def _get_shelf_by_code(db: AsyncSession, code: str) -> Shelf | None:
    result = await db.execute(select(Shelf).where(Shelf.code == code))
    return result.scalar_one_or_none()


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
