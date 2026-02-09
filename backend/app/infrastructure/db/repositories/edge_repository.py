from typing import Optional, Sequence, Iterable

from sqlalchemy import delete, select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.edge import EdgeModel


class SQLAlchemyEdgeRepository:
    """
    Репозиторий для Edge на Async SQLAlchemy.

    ВАЖНО:
    - Репозиторий НЕ делает commit/rollback.
    - Он работает в рамках внешней транзакции (UnitOfWork / session.begin()).
    - Для применения изменений в текущей транзакции используем flush().

    Контракт методов:
    - create_edge: добавляет Edge в сессию, делает flush, возвращает объект (обычно уже с id).
    - read_edge: возвращает Edge или None, если не найдено.
    - read_edges: возвращает список всех рёбер.
    - read_edges_by_warehouse: возвращает список рёбер конкретного склада.
    - update_edge: сохраняет изменения (через merge + flush) и возвращает прикреплённый объект.
    - delete_edge: возвращает True, если запись удалена, иначе False.
    - delete_edges_by_warehouse: удаляет рёбра склада, возвращает True если удалено хотя бы что-то.
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession обычно создаётся и управляется UnitOfWork
        self._session = session

    async def create_edge(self, edge: EdgeModel) -> EdgeModel:
        # Добавляем объект в сессию (в БД уйдёт после flush)
        self._session.add(edge)

        # Flush отправляет INSERT в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД (server_default/trigger и т.п.)
        await self._session.refresh(edge)
        return edge

    async def create_edges_by_warehouse(self, edges: Iterable[dict], warehouse_id: int) -> None:
        rows = [dict(e) for e in edges]
        if not rows:
            return

        for r in rows:
            r["warehouse_id"] = warehouse_id

        await self._session.execute(insert(EdgeModel).values(rows))
        await self._session.flush()

    async def read_edge(self, edge_id: int) -> Optional[EdgeModel]:
        stmt = select(EdgeModel).where(EdgeModel.id == edge_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_edges(self) -> Sequence[EdgeModel]:
        stmt = select(EdgeModel).order_by(EdgeModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_edges_by_warehouse(self, warehouse_id: int) -> Sequence[EdgeModel]:
        stmt = (
            select(EdgeModel)
            .where(EdgeModel.warehouse_id == warehouse_id)
            .order_by(EdgeModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_edge(self, edge: EdgeModel) -> EdgeModel:
        # merge полезен, если объект detached; вернёт инстанс, прикреплённый к session
        merged = await self._session.merge(edge)

        # Flush отправляет UPDATE в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД
        await self._session.refresh(merged)
        return merged

    async def delete_edge(self, edge_id: int) -> bool:
        stmt = delete(EdgeModel).where(EdgeModel.id == edge_id)
        result = await self._session.execute(stmt)

        # Flush фиксирует удаление в текущей транзакции (без commit).
        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_edges_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(EdgeModel).where(EdgeModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)