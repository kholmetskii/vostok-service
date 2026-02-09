from sqlalchemy import Column, Integer, String, Float
from app.infrastructure.db.base import Base

class WarehouseModel(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    width_m = Column(Float, nullable=False)
    length_m = Column(Float, nullable=False)
    floor_count = Column(Integer, nullable=False)
