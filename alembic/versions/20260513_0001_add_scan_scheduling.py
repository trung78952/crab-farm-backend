"""add scan scheduling

Revision ID: 20260513_0001
Revises: 25734ec88201
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0001"
down_revision: Union[str, None] = "25734ec88201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("scan_mode", sa.String(length=32), nullable=False),
        sa.Column("tank_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scan_schedules")),
        if_not_exists=True,
    )
    op.create_table(
        "scan_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scan_mode", sa.String(length=32), nullable=False),
        sa.Column("total_tanks", sa.Integer(), nullable=False),
        sa.Column("completed_tanks", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["schedule_id"],
            ["scan_schedules.id"],
            name=op.f("fk_scan_jobs_schedule_id_scan_schedules"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scan_jobs")),
        if_not_exists=True,
    )
    op.create_table(
        "scan_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["detection_id"],
            ["detections.id"],
            name=op.f("fk_scan_job_items_detection_id_detections"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"],
            ["images.id"],
            name=op.f("fk_scan_job_items_image_id_images"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scan_job_id"],
            ["scan_jobs.id"],
            name=op.f("fk_scan_job_items_scan_job_id_scan_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tank_id"],
            ["tanks.id"],
            name=op.f("fk_scan_job_items_tank_id_tanks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scan_job_items")),
        if_not_exists=True,
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_schedules_is_active ON scan_schedules (is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_schedules_next_run_at ON scan_schedules (next_run_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_schedules_scan_mode ON scan_schedules (scan_mode)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_jobs_schedule_id ON scan_jobs (schedule_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_jobs_scan_mode ON scan_jobs (scan_mode)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_jobs_status ON scan_jobs (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_job_items_scan_job_id ON scan_job_items (scan_job_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_job_items_tank_id ON scan_job_items (tank_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scan_job_items_status ON scan_job_items (status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scan_job_items_status")
    op.execute("DROP INDEX IF EXISTS ix_scan_job_items_tank_id")
    op.execute("DROP INDEX IF EXISTS ix_scan_job_items_scan_job_id")
    op.execute("DROP INDEX IF EXISTS ix_scan_jobs_status")
    op.execute("DROP INDEX IF EXISTS ix_scan_jobs_scan_mode")
    op.execute("DROP INDEX IF EXISTS ix_scan_jobs_schedule_id")
    op.execute("DROP INDEX IF EXISTS ix_scan_schedules_scan_mode")
    op.execute("DROP INDEX IF EXISTS ix_scan_schedules_next_run_at")
    op.execute("DROP INDEX IF EXISTS ix_scan_schedules_is_active")
    op.drop_table("scan_job_items", if_exists=True)
    op.drop_table("scan_jobs", if_exists=True)
    op.drop_table("scan_schedules", if_exists=True)
