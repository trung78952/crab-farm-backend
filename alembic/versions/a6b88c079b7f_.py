"""empty message

Revision ID: a6b88c079b7f
Revises: 20260513_0002
Create Date: 2026-05-13 14:51:55.790653
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = 'a6b88c079b7f'
down_revision: Union[str, None] = '20260513_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
