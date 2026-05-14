"""multi shelf realtime ai architecture

Revision ID: 20260514_0003
Revises: a6b88c079b7f
Create Date: 2026-05-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260514_0003"
down_revision = "a6b88c079b7f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shelves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("motion_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["motion_device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["camera_device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_shelves_code ON shelves (code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shelves_status ON shelves (status)")

    op.add_column("devices", sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_devices_shelf_id_shelves", "devices", "shelves", ["shelf_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_devices_shelf_id", "devices", ["shelf_id"], if_not_exists=True)

    op.add_column("tanks", sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_tanks_shelf_id_shelves", "tanks", "shelves", ["shelf_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_tanks_shelf_id", "tanks", ["shelf_id"], if_not_exists=True)

    op.add_column("scan_schedules", sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("scan_schedules", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    op.create_foreign_key("fk_scan_schedules_shelf_id_shelves", "scan_schedules", "shelves", ["shelf_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_scan_schedules_shelf_id", "scan_schedules", ["shelf_id"], if_not_exists=True)
    op.create_index("ix_scan_schedules_priority", "scan_schedules", ["priority"], if_not_exists=True)

    op.add_column("scan_jobs", sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("scan_jobs", sa.Column("job_type", sa.String(length=32), nullable=False, server_default="manual_scan"))
    op.add_column("scan_jobs", sa.Column("priority", sa.Integer(), nullable=False, server_default="100"))
    op.add_column("scan_jobs", sa.Column("failed_tanks", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scan_jobs", sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("scan_jobs", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_foreign_key("fk_scan_jobs_shelf_id_shelves", "scan_jobs", "shelves", ["shelf_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_scan_jobs_shelf_id", "scan_jobs", ["shelf_id"], if_not_exists=True)
    op.create_index("ix_scan_jobs_job_type", "scan_jobs", ["job_type"], if_not_exists=True)
    op.create_index("ix_scan_jobs_priority", "scan_jobs", ["priority"], if_not_exists=True)
    op.create_index("ix_scan_jobs_is_simulation", "scan_jobs", ["is_simulation"], if_not_exists=True)

    op.add_column("scan_job_items", sa.Column("motion_command_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("scan_job_items", sa.Column("camera_command_id", sa.String(length=128), nullable=True))
    op.create_foreign_key("fk_scan_job_items_motion_command_id_motion_commands", "scan_job_items", "motion_commands", ["motion_command_id"], ["id"], ondelete="SET NULL")

    op.add_column("mqtt_logs", sa.Column("raw_payload", sa.Text(), nullable=True))
    op.add_column("mqtt_logs", sa.Column("retain", sa.Boolean(), nullable=True))

    op.add_column("images", sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_images_is_simulation", "images", ["is_simulation"], if_not_exists=True)

    op.add_column("detections", sa.Column("model_version", sa.String(length=128), nullable=True))
    op.add_column("detections", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("detections", sa.Column("human_label", sa.String(length=128), nullable=True))
    op.add_column("detections", sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("detections", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("detections", sa.Column("is_simulation", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_foreign_key("fk_detections_verified_by_users", "detections", "users", ["verified_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_detections_is_verified", "detections", ["is_verified"], if_not_exists=True)
    op.create_index("ix_detections_is_simulation", "detections", ["is_simulation"], if_not_exists=True)

    op.create_table(
        "ai_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=False),
        sa.Column("model_path", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_models_is_active", "ai_models", ["is_active"], if_not_exists=True)

    op.create_table(
        "recheck_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_detection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_detection_id"], ["detections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recheck_tasks_status", "recheck_tasks", ["status"], if_not_exists=True)
    op.create_index("ix_recheck_tasks_run_at", "recheck_tasks", ["run_at"], if_not_exists=True)
    op.create_index("ix_recheck_tasks_priority", "recheck_tasks", ["priority"], if_not_exists=True)

    op.create_table(
        "training_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ai_label", sa.String(length=128), nullable=True),
        sa.Column("human_label", sa.String(length=128), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dataset_split", sa.String(length=16), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["detection_id"], ["detections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_samples_is_verified", "training_samples", ["is_verified"], if_not_exists=True)
    op.create_index("ix_training_samples_dataset_split", "training_samples", ["dataset_split"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("training_samples", if_exists=True)
    op.drop_table("recheck_tasks", if_exists=True)
    op.drop_table("ai_models", if_exists=True)
    op.drop_table("shelves", if_exists=True)
