from alembic import op
import sqlalchemy as sa


revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("floor_count", sa.Integer(), nullable=False),
    )

    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ext_id", sa.Integer(), nullable=False),
        sa.Column("floor_level", sa.Integer(), nullable=False),
        sa.Column("x_m", sa.Float(), nullable=False),
        sa.Column("y_m", sa.Float(), nullable=False),
        sa.UniqueConstraint("warehouse_id", "ext_id", name="uq_nodes_warehouse_ext"),
    )

    op.create_table(
        "shelves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ext_id", sa.Integer(), nullable=False),
        sa.Column("floor_level", sa.Integer(), nullable=False),
        sa.Column("x_m", sa.Float(), nullable=False),
        sa.Column("y_m", sa.Float(), nullable=False),
        sa.Column("width_m", sa.Float(), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("shelving_code", sa.String(length=100), nullable=False),
        sa.Column("section_code", sa.String(length=100), nullable=False),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False),
        sa.UniqueConstraint("warehouse_id", "ext_id", name="uq_shelves_warehouse_ext"),
    )

    op.create_table(
        "edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ext_id", sa.Integer(), nullable=False),
        sa.Column("from_node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("a_node_id", sa.Integer(), sa.Computed("LEAST(from_node_id, to_node_id)", persisted=True)),
        sa.Column("b_node_id", sa.Integer(), sa.Computed("GREATEST(from_node_id, to_node_id)", persisted=True)),
        sa.CheckConstraint("from_node_id <> to_node_id", name="ck_edges_distinct_nodes"),
        sa.UniqueConstraint("warehouse_id", "ext_id", name="uq_edges_warehouse_ext"),
        sa.UniqueConstraint("warehouse_id", "a_node_id", "b_node_id", name="uq_edges_undirected"),
    )

    op.create_table(
        "obstacles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ext_id", sa.Integer(), nullable=False),
        sa.Column("from_node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_node_id", sa.Integer(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("a_node_id", sa.Integer(), sa.Computed("LEAST(from_node_id, to_node_id)", persisted=True)),
        sa.Column("b_node_id", sa.Integer(), sa.Computed("GREATEST(from_node_id, to_node_id)", persisted=True)),
        sa.CheckConstraint("from_node_id <> to_node_id", name="ck_obstacles_distinct_nodes"),
        sa.UniqueConstraint("warehouse_id", "ext_id", name="uq_obstacles_warehouse_ext"),
        sa.UniqueConstraint("warehouse_id", "a_node_id", "b_node_id", name="uq_obstacles_undirected"),
    )


def downgrade():
    op.drop_table("obstacles")
    op.drop_table("edges")
    op.drop_table("shelves")
    op.drop_table("nodes")
    op.drop_table("warehouses")
