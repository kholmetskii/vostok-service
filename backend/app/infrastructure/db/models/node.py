from sqlalchemy import Column, Float, ForeignKey, Integer, UniqueConstraint

from app.infrastructure.db.base import Base


class NodeModel(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    ext_id = Column(Integer, nullable=False)

    floor_level = Column(Integer, nullable=False)
    x_m = Column(Float, nullable=False)
    y_m = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("warehouse_id", "ext_id", name="uq_nodes_warehouse_ext"),)
