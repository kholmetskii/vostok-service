from collections.abc import Iterable, Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.shelf import ShelfModel


class SQLAlchemyShelfRepository:
    """Persist shelves without owning the surrounding transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_shelf(self, shelf: ShelfModel) -> ShelfModel:
        self._session.add(shelf)
        await self._session.flush()
        await self._session.refresh(shelf)
        return shelf

    async def create_shelves_by_warehouse(self, shelves: Iterable[dict], warehouse_id: int) -> None:
        rows = [dict(s) for s in shelves]
        if not rows:
            return

        for r in rows:
            r["warehouse_id"] = warehouse_id

        await self._session.execute(insert(ShelfModel).values(rows))
        await self._session.flush()

    async def read_shelf(self, shelf_id: int) -> ShelfModel | None:
        stmt = select(ShelfModel).where(ShelfModel.id == shelf_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_shelves(self) -> Sequence[ShelfModel]:
        stmt = select(ShelfModel).order_by(ShelfModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_shelves_by_warehouse(self, warehouse_id: int) -> Sequence[ShelfModel]:
        stmt = (
            select(ShelfModel)
            .where(ShelfModel.warehouse_id == warehouse_id)
            .order_by(ShelfModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_shelf_by_ext_id(self, warehouse_id: int, shelf_ext_id: int) -> ShelfModel | None:
        stmt = select(ShelfModel).where(
            ShelfModel.warehouse_id == warehouse_id,
            ShelfModel.ext_id == shelf_ext_id,
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_shelf(self, shelf: ShelfModel) -> ShelfModel:
        merged = await self._session.merge(shelf)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_shelf(self, shelf_id: int) -> bool:
        stmt = delete(ShelfModel).where(ShelfModel.id == shelf_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_shelves_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(ShelfModel).where(ShelfModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)
