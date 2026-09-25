from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.warehouse import WarehouseModel


class SQLAlchemyWarehouseRepository:
    """Persist warehouses without owning the surrounding transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_warehouse(self, warehouse: WarehouseModel) -> WarehouseModel:
        self._session.add(warehouse)
        await self._session.flush()
        await self._session.refresh(warehouse)
        return warehouse

    async def read_warehouse(self, warehouse_id: int) -> WarehouseModel | None:
        stmt = select(WarehouseModel).where(WarehouseModel.id == warehouse_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_warehouses(self) -> Sequence[WarehouseModel]:
        stmt = select(WarehouseModel).order_by(WarehouseModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_warehouse(self, warehouse: WarehouseModel) -> WarehouseModel:
        merged = await self._session.merge(warehouse)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(WarehouseModel).where(WarehouseModel.id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)
