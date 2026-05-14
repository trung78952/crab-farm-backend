from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.detection import Detection
from app.models.image import Image
from app.models.training_sample import TrainingSample
from app.schemas.training_sample import TrainingSampleLabelRequest

CLASS_NAMES = ["crab_normal", "crab_molting", "crab_soft_shell", "empty_tank", "uncertain_or_bad_image"]


async def create_from_detection(db: AsyncSession, detection_id: UUID) -> TrainingSample:
    detection = await db.get(Detection, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Detection not found")
    sample = TrainingSample(
        image_id=detection.image_id,
        detection_id=detection.id,
        tank_id=detection.tank_id,
        ai_label=detection.class_name,
        bbox=detection.bbox,
    )
    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    return sample


async def list_samples(db: AsyncSession, verified: bool | None = None) -> list[TrainingSample]:
    stmt = select(TrainingSample).order_by(TrainingSample.created_at.desc())
    if verified is not None:
        stmt = stmt.where(TrainingSample.is_verified.is_(verified))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def label_sample(db: AsyncSession, sample_id: UUID, data: TrainingSampleLabelRequest, user_id: UUID) -> TrainingSample:
    sample = await db.get(TrainingSample, sample_id)
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training sample not found")
    sample.human_label = data.human_label
    sample.bbox = data.bbox if data.bbox is not None else sample.bbox
    sample.dataset_split = data.dataset_split
    sample.note = data.note
    sample.is_verified = True
    sample.verified_by = user_id
    sample.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sample)
    return sample


async def export_yolo_dataset(db: AsyncSession) -> dict:
    result = await db.execute(select(TrainingSample).where(TrainingSample.is_verified.is_(True)))
    samples = list(result.scalars().all())
    export_dir = Path(settings.storage_dir) / "datasets" / f"export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    for split in ("train", "val", "test"):
        (export_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (export_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    exported = 0
    for sample in samples:
        image = await db.get(Image, sample.image_id)
        if image is None or not sample.human_label:
            continue
        split = sample.dataset_split or "train"
        source = Path(image.image_path)
        if source.exists():
            shutil.copy2(source, export_dir / "images" / split / source.name)
        label_index = CLASS_NAMES.index(sample.human_label) if sample.human_label in CLASS_NAMES else 0
        label_path = export_dir / "labels" / split / f"{source.stem}.txt"
        label_path.write_text(_bbox_to_yolo(label_index, sample.bbox), encoding="utf-8")
        exported += 1

    (export_dir / "data.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/val\ntest: images/test\n"
        f"names: {CLASS_NAMES}\n"
        "# MVP export writes default full-image bbox when bbox is missing or not normalized.\n",
        encoding="utf-8",
    )
    return {
        "export_dir": str(export_dir),
        "samples_exported": exported,
        "note": "MVP exporter uses full-image bbox when source bbox is missing or not YOLO-normalized.",
    }


def _bbox_to_yolo(label_index: int, bbox: dict | None) -> str:
    if not bbox:
        return f"{label_index} 0.5 0.5 1.0 1.0\n"
    if {"x_center", "y_center", "width", "height"}.issubset(bbox):
        return f"{label_index} {bbox['x_center']} {bbox['y_center']} {bbox['width']} {bbox['height']}\n"
    return f"{label_index} 0.5 0.5 1.0 1.0\n"
