from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint

from app.infrastructure.db.base import Base


class ShelfModel(Base):
    __tablename__ = "shelves"

    id = Column(Integer, primary_key=True)

    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    ext_id = Column(Integer, nullable=False)

    floor_level = Column(Integer, nullable=False)

    x_m = Column(Float, nullable=False)
    y_m = Column(Float, nullable=False)
    width_m = Column(Float, nullable=False)
    length_m = Column(Float, nullable=False)

    shelving_code = Column(String(100), nullable=False)
    section_code = Column(String(100), nullable=False)

    node_id = Column(Integer, ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (UniqueConstraint("warehouse_id", "ext_id", name="uq_shelves_warehouse_ext"),)
