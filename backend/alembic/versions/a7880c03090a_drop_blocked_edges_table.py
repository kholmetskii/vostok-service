"""drop blocked_edges table

Revision ID: a7880c03090a
Revises: 3a5a64108108
Create Date: 2026-02-09 20:42:12.489584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7880c03090a'
down_revision: Union[str, Sequence[str], None] = '3a5a64108108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("blocked_edges")


def downgrade() -> None:
    op.create_table(
        "blocked_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_ext_id", sa.Integer(), nullable=False),
        sa.UniqueConstraint("warehouse_id", "edge_ext_id", name="uq_blocked_edges_warehouse_edge_ext"),
    )
