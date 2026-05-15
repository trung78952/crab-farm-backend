"""sensors schedules queue

Revision ID: 20260515_0004
Revises: 20260514_0003
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260515_0004"
down_revision = "20260514_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scan_schedules", sa.Column("schedule_type", sa.String(length=32), nullable=False, server_default="user_periodic"))
    op.add_column("scan_schedules", sa.Column("tag", sa.String(length=16), nullable=False, server_default="USER"))
    op.alter_column("scan_schedules", "interval_minutes", existing_type=sa.Integer(), nullable=True)
    op.add_column("scan_schedules", sa.Column("run_once", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("scan_schedules", sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("scan_schedules", sa.Column("max_runs", sa.Integer(), nullable=True))
    op.add_column("scan_schedules", sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scan_schedules", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scan_schedules", sa.Column("stop_condition", sa.String(length=64), nullable=True))
    op.add_column("scan_schedules", sa.Column("created_by_system", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("scan_schedules", sa.Column("auto_reason", sa.String(length=64), nullable=True))
    op.add_column("scan_schedules", sa.Column("parent_detection_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("scan_schedules", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_scan_schedules_parent_detection_id_detections",
        "scan_schedules",
        "detections",
        ["parent_detection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_scan_schedules_schedule_type", "scan_schedules", ["schedule_type"], if_not_exists=True)
    op.create_index("ix_scan_schedules_tag", "scan_schedules", ["tag"], if_not_exists=True)
    op.create_index("ix_scan_schedules_created_by_system", "scan_schedules", ["created_by_system"], if_not_exists=True)
    op.create_index("ix_scan_schedules_auto_reason", "scan_schedules", ["auto_reason"], if_not_exists=True)

    op.create_table(
        "sensor_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_sensor_types_code", "sensor_types", ["code"], if_not_exists=True)

    op.create_table(
        "sensors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sensor_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tank_id IS NOT NULL OR shelf_id IS NOT NULL", name="ck_sensors_has_owner"),
        sa.ForeignKeyConstraint(["sensor_type_id"], ["sensor_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shelf_id"], ["shelves.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    for col in ["code", "sensor_type_id", "tank_id", "shelf_id", "device_id", "status"]:
        op.create_index(f"ix_sensors_{col}", "sensors", [col], if_not_exists=True)

    op.create_table(
        "sensor_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shelf_id"], ["shelves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["sensor_id", "tank_id", "shelf_id", "measured_at"]:
        op.create_index(f"ix_sensor_readings_{col}", "sensor_readings", [col], if_not_exists=True)

    op.create_table(
        "sensor_alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensor_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sensor_type_id"], ["sensor_types.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shelf_id"], ["shelves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["sensor_type_id", "tank_id", "shelf_id", "is_active"]:
        op.create_index(f"ix_sensor_alert_rules_{col}", "sensor_alert_rules", [col], if_not_exists=True)

    op.create_table(
        "sensor_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reading_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alert_type", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sensor_id"], ["sensors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reading_id"], ["sensor_readings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shelf_id"], ["shelves.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for col in ["sensor_id", "reading_id", "tank_id", "shelf_id", "alert_type", "status"]:
        op.create_index(f"ix_sensor_alerts_{col}", "sensor_alerts", [col], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("sensor_alerts", if_exists=True)
    op.drop_table("sensor_alert_rules", if_exists=True)
    op.drop_table("sensor_readings", if_exists=True)
    op.drop_table("sensors", if_exists=True)
    op.drop_table("sensor_types", if_exists=True)
    op.drop_constraint("fk_scan_schedules_parent_detection_id_detections", "scan_schedules", type_="foreignkey")
    for col in [
        "completed_at",
        "parent_detection_id",
        "auto_reason",
        "created_by_system",
        "stop_condition",
        "expires_at",
        "start_at",
        "max_runs",
        "run_count",
        "run_once",
        "tag",
        "schedule_type",
    ]:
        op.drop_column("scan_schedules", col)
    op.alter_column("scan_schedules", "interval_minutes", existing_type=sa.Integer(), nullable=False)
