"""initial schema

Revision ID: 25734ec88201
Revises:
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "25734ec88201"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tanks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("level_index", sa.Integer(), nullable=False),
        sa.Column("x_position", sa.Float(), nullable=False),
        sa.Column("y_position", sa.Float(), nullable=False),
        sa.Column("z_position", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tanks")),
        sa.UniqueConstraint("code", name=op.f("uq_tanks_code")),
        if_not_exists=True,
    )
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mqtt_client_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("code", name=op.f("uq_devices_code")),
        if_not_exists=True,
    )
    op.create_table(
        "images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name=op.f("fk_images_device_id_devices"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], name=op.f("fk_images_tank_id_tanks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_images")),
        if_not_exists=True,
    )
    op.create_table(
        "motion_commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cmd_id", sa.String(length=64), nullable=False),
        sa.Column("command_type", sa.String(length=32), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mqtt_topic", sa.String(length=255), nullable=False),
        sa.Column("mqtt_response", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], name=op.f("fk_motion_commands_tank_id_tanks"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_motion_commands")),
        sa.UniqueConstraint("cmd_id", name=op.f("uq_motion_commands_cmd_id")),
        if_not_exists=True,
    )
    op.create_table(
        "detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_name", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["image_id"], ["images.id"], name=op.f("fk_detections_image_id_images"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], name=op.f("fk_detections_tank_id_tanks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_detections")),
        if_not_exists=True,
    )
    op.create_table(
        "harvests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("motion_command_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["detection_id"], ["detections.id"], name=op.f("fk_harvests_detection_id_detections"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["motion_command_id"], ["motion_commands.id"], name=op.f("fk_harvests_motion_command_id_motion_commands"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tank_id"], ["tanks.id"], name=op.f("fk_harvests_tank_id_tanks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_harvests")),
        if_not_exists=True,
    )
    op.create_table(
        "mqtt_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("qos", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mqtt_logs")),
        if_not_exists=True,
    )
    for table, cols in {
        "tanks": ["code", "status"],
        "devices": ["code", "type", "status"],
        "images": ["tank_id", "kind"],
        "motion_commands": ["cmd_id", "command_type", "status"],
        "detections": ["tank_id", "image_id", "class_name", "action"],
        "harvests": ["tank_id", "status"],
        "mqtt_logs": ["direction", "topic"],
    }.items():
        for col in cols:
            op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table} ({col})")


def downgrade() -> None:
    for table, cols in {
        "mqtt_logs": ["topic", "direction"],
        "harvests": ["status", "tank_id"],
        "detections": ["action", "class_name", "image_id", "tank_id"],
        "motion_commands": ["status", "command_type", "cmd_id"],
        "images": ["kind", "tank_id"],
        "devices": ["status", "type", "code"],
        "tanks": ["status", "code"],
    }.items():
        for col in cols:
            op.execute(f"DROP INDEX IF EXISTS ix_{table}_{col}")
    op.drop_table("mqtt_logs", if_exists=True)
    op.drop_table("harvests", if_exists=True)
    op.drop_table("detections", if_exists=True)
    op.drop_table("motion_commands", if_exists=True)
    op.drop_table("images", if_exists=True)
    op.drop_table("devices", if_exists=True)
    op.drop_table("tanks", if_exists=True)
