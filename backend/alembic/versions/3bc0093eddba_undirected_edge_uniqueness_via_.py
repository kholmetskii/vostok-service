"""undirected edge uniqueness via expression index

Revision ID: 3bc0093eddba
Revises: 0001_init_schema
Create Date: 2025-12-28 20:43:27.558532

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = '3bc0093eddba'
down_revision = '0001_init_schema'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_edges_undirected", "edges", type_="unique")
    op.drop_column("edges", "a_node_id")
    op.drop_column("edges", "b_node_id")

    op.execute("""
        CREATE UNIQUE INDEX ux_edges_undirected
        ON edges (
            warehouse_id,
            LEAST(from_node_id, to_node_id),
            GREATEST(from_node_id, to_node_id)
        );
    """)

    op.drop_constraint("uq_obstacles_undirected", "obstacles", type_="unique")
    op.drop_column("obstacles", "a_node_id")
    op.drop_column("obstacles", "b_node_id")

    op.execute("""
        CREATE UNIQUE INDEX ux_obstacles_undirected
        ON obstacles (
            warehouse_id,
            LEAST(from_node_id, to_node_id),
            GREATEST(from_node_id, to_node_id)
        );
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS ux_obstacles_undirected;")
    op.execute("DROP INDEX IF EXISTS ux_edges_undirected;")


    op.execute("""
        ALTER TABLE edges
        ADD COLUMN a_node_id INTEGER GENERATED ALWAYS AS (LEAST(from_node_id, to_node_id)) STORED,
        ADD COLUMN b_node_id INTEGER GENERATED ALWAYS AS (GREATEST(from_node_id, to_node_id)) STORED;
    """)
    op.create_unique_constraint("uq_edges_undirected", "edges", ["warehouse_id", "a_node_id", "b_node_id"])

    op.execute("""
        ALTER TABLE obstacles
        ADD COLUMN a_node_id INTEGER GENERATED ALWAYS AS (LEAST(from_node_id, to_node_id)) STORED,
        ADD COLUMN b_node_id INTEGER GENERATED ALWAYS AS (GREATEST(from_node_id, to_node_id)) STORED;
    """)
    op.create_unique_constraint("uq_obstacles_undirected", "obstacles", ["warehouse_id", "a_node_id", "b_node_id"])
