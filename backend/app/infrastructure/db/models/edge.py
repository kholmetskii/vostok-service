from sqlalchemy import CheckConstraint, Column, Float, ForeignKey, Integer, UniqueConstraint

from app.infrastructure.db.base import Base


class EdgeModel(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    ext_id = Column(Integer, nullable=False)

    from_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)

    weight_multiplier = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        CheckConstraint("from_node_id <> to_node_id", name="ck_edges_distinct_nodes"),
        UniqueConstraint("warehouse_id", "ext_id", name="uq_edges_warehouse_ext"),
    )
