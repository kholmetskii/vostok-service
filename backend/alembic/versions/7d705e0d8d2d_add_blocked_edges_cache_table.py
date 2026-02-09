"""add blocked_edges cache table

Revision ID: 7d705e0d8d2d
Revises: 3eb37841e06b
Create Date: 2026-01-10 14:36:23.058577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d705e0d8d2d'
down_revision: Union[str, Sequence[str], None] = '3eb37841e06b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blocked_edges",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("warehouse_id", sa.BigInteger(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_id", sa.BigInteger(), sa.ForeignKey("edges.id", ondelete="CASCADE"), nullable=False),
        sa.Column("obstacle_id", sa.BigInteger(), sa.ForeignKey("obstacles.id", ondelete="CASCADE"), nullable=False),
    )

    op.create_unique_constraint(
        "uq_blocked_edges_wh_edge_obstacle",
        "blocked_edges",
        ["warehouse_id", "edge_id", "obstacle_id"],
    )

    op.create_index(
        "ix_blocked_edges_wh_edge",
        "blocked_edges",
        ["warehouse_id", "edge_id"],
    )
    op.create_index(
        "ix_blocked_edges_wh_obstacle",
        "blocked_edges",
        ["warehouse_id", "obstacle_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_blocked_edges_wh_obstacle", table_name="blocked_edges")
    op.drop_index("ix_blocked_edges_wh_edge", table_name="blocked_edges")
    op.drop_constraint("uq_blocked_edges_wh_edge_obstacle", "blocked_edges", type_="unique")
    op.drop_table("blocked_edges")
