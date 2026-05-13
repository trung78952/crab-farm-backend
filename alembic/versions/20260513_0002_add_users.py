"""add users

Revision ID: 20260513_0002
Revises: 20260513_0001
Create Date: 2026-05-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260513_0002"
down_revision: Union[str, None] = "20260513_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        if_not_exists=True,
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_is_active")
    op.execute("DROP INDEX IF EXISTS ix_users_role")
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.drop_table("users", if_exists=True)
