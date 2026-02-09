from typing import Optional, Sequence, Iterable

from sqlalchemy import delete, select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.shelf import ShelfModel


class SQLAlchemyShelfRepository:
    """
    Репозиторий для Shelf на Async SQLAlchemy.

    ВАЖНО:
    - Репозиторий НЕ делает commit/rollback.
    - Он работает в рамках внешней транзакции (UnitOfWork / session.begin()).
    - Для применения изменений в текущей транзакции используем flush().

    Контракт методов:
    - create_shelf: добавляет Shelf в сессию, делает flush, возвращает объект (обычно уже с id).
    - read_shelf: возвращает Shelf или None, если не найдено.
    - read_shelves: возвращает список всех полок.
    - read_shelves_by_warehouse: возвращает полки конкретного склада.
    - update_shelf: сохраняет изменения (через merge + flush) и возвращает прикреплённый объект.
    - delete_shelf: возвращает True, если запись удалена, иначе False.
    - delete_shelves_by_warehouse: удаляет полки склада, возвращает True если удалено хотя бы что-то.
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession обычно создаётся и управляется UnitOfWork
        self._session = session

    async def create_shelf(self, shelf: ShelfModel) -> ShelfModel:
        # Добавляем объект в сессию (в БД уйдёт после flush)
        self._session.add(shelf)

        # Flush отправляет INSERT в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД (server_default/trigger и т.п.)
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

    async def read_shelf(self, shelf_id: int) -> Optional[ShelfModel]:
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
        stmt = (
            select(ShelfModel)
            .where(
                ShelfModel.warehouse_id == warehouse_id,
                ShelfModel.ext_id == shelf_ext_id,
            )
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def update_shelf(self, shelf: ShelfModel) -> ShelfModel:
        # merge полезен, если объект detached; вернёт инстанс, прикреплённый к session
        merged = await self._session.merge(shelf)

        # Flush отправляет UPDATE в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД
        await self._session.refresh(merged)
        return merged

    async def delete_shelf(self, shelf_id: int) -> bool:
        stmt = delete(ShelfModel).where(ShelfModel.id == shelf_id)
        result = await self._session.execute(stmt)

        # Flush фиксирует удаление в текущей транзакции (без commit).
        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_shelves_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(ShelfModel).where(ShelfModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)