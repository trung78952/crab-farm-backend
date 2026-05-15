from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.database import get_db
from app.schemas.sensor import SensorAlertRuleCreate, SensorAlertRuleRead, SensorAlertRuleUpdate
from app.services import sensor_service

router = APIRouter()


@router.get("", response_model=list[SensorAlertRuleRead])
async def list_sensor_alert_rules(db: AsyncSession = Depends(get_db)):
    return await sensor_service.list_sensor_alert_rules(db)


@router.post("", response_model=SensorAlertRuleRead, dependencies=[Depends(require_roles("operator"))])
async def create_sensor_alert_rule(data: SensorAlertRuleCreate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.create_sensor_alert_rule(db, data)


@router.patch("/{rule_id}", response_model=SensorAlertRuleRead, dependencies=[Depends(require_roles("operator"))])
async def update_sensor_alert_rule(rule_id: UUID, data: SensorAlertRuleUpdate, db: AsyncSession = Depends(get_db)):
    return await sensor_service.update_sensor_alert_rule(db, rule_id, data)
