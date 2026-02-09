"""remove is_blocked from edges

Revision ID: 3a5a64108108
Revises: 7d705e0d8d2d
Create Date: 2026-01-10 17:23:05.109789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a5a64108108'
down_revision: Union[str, Sequence[str], None] = '7d705e0d8d2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("edges", "is_blocked")


def downgrade() -> None:
    op.add_column(
        "edges",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false())
    )
