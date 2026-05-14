from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_model import AiModel
from app.schemas.ai import AiModelActivateRequest
from app.services.realtime_service import realtime_service

DEFAULT_CLASSES = ["crab_normal", "crab_molting", "crab_soft_shell", "empty_tank", "uncertain_or_bad_image"]


async def list_models(db: AsyncSession) -> list[AiModel]:
    result = await db.execute(select(AiModel).order_by(AiModel.created_at.desc()))
    return list(result.scalars().all())


async def get_or_create_active_model(db: AsyncSession) -> AiModel:
    result = await db.execute(select(AiModel).where(AiModel.is_active.is_(True)).limit(1))
    model = result.scalar_one_or_none()
    if model is not None:
        return model

    model = AiModel(
        name=settings.ai_model_version,
        version=settings.ai_model_version,
        model_path=settings.ai_model_path,
        is_active=True,
        classes=DEFAULT_CLASSES,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def activate_model(db: AsyncSession, data: AiModelActivateRequest) -> AiModel:
    await db.execute(update(AiModel).values(is_active=False))
    model = AiModel(
        name=data.name or data.model_version,
        version=data.model_version,
        model_path=data.model_path,
        is_active=True,
        classes=data.classes or DEFAULT_CLASSES,
        activated_at=datetime.now(timezone.utc),
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    await realtime_service.broadcast("ai_model_changed", {"model_path": model.model_path, "version": model.version})
    return model
