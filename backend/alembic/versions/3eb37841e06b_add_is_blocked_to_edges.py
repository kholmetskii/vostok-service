"""add is_blocked to edges

Revision ID: 3eb37841e06b
Revises: 3bc0093eddba
Create Date: 2026-01-05 03:20:33.232682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eb37841e06b'
down_revision: Union[str, Sequence[str], None] = '3bc0093eddba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None




def upgrade():
    op.add_column(
        "edges",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # optional: remove server default after backfilling (not required)
    op.alter_column("edges", "is_blocked", server_default=None)

    # optional index (good for large graphs)
    op.create_index("ix_edges_wh_blocked", "edges", ["warehouse_id", "is_blocked"])

def downgrade():
    op.drop_index("ix_edges_wh_blocked", table_name="edges")
    op.drop_column("edges", "is_blocked")
