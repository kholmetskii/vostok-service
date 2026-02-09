from sqlalchemy import (
    Column, Integer, ForeignKey, UniqueConstraint, CheckConstraint, Computed
)
from app.infrastructure.db.base import Base

class ObstacleModel(Base):
    __tablename__ = "obstacles"

    id = Column(Integer, primary_key=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    ext_id = Column(Integer, nullable=False)

    from_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    to_node_id = Column(Integer, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        CheckConstraint("from_node_id <> to_node_id", name="ck_obstacles_distinct_nodes"),
        UniqueConstraint("warehouse_id", "ext_id", name="uq_obstacles_warehouse_ext"),
    )
