from typing import Optional, Sequence, Iterable

from sqlalchemy import delete, select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.node import NodeModel


class SQLAlchemyNodeRepository():
    """
    Репозиторий для Node на Async SQLAlchemy.

    ВАЖНО:
    - Репозиторий НЕ делает commit/rollback.
    - Он работает в рамках внешней транзакции (UnitOfWork / session.begin()).
    - Для применения изменений в текущей транзакции используем flush().

    Контракт методов:
    - create_node: добавляет Node в сессию, делает flush, возвращает объект (обычно уже с id).
    - read_node: возвращает Node или None, если не найдено.
    - read_nodes: возвращает список всех узлов.
    - read_nodes_by_warehouse: возвращает список узлов конкретного склада.
    - update_node: сохраняет изменения (через merge + flush) и возвращает прикреплённый объект.
    - delete_node: возвращает True, если запись удалена, иначе False.
    - delete_nodes_by_warehouse: удаляет узлы склада, возвращает True если удалено хотя бы что-то.
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession обычно создаётся и управляется UnitOfWork
        self._session = session

    async def create_node(self, node: NodeModel) -> NodeModel:
        # Добавляем объект в сессию (в БД уйдёт после flush)
        self._session.add(node)

        # Flush отправляет INSERT в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД (server_default/trigger и т.п.)
        await self._session.refresh(node)
        return node

    async def create_nodes_by_warehouse(self, nodes: Iterable[dict], warehouse_id: int) -> None:
        rows = [dict(n) for n in nodes]
        if not rows:
            return
        for r in rows:
            r["warehouse_id"] = warehouse_id

        await self._session.execute(insert(NodeModel).values(rows))
        await self._session.flush()

    async def get_id_map_by_ext_ids(self, warehouse_id: int, ext_ids: set[int]) -> dict[int, int]:
        if not ext_ids:
            return {}

        stmt = (
            select(NodeModel.ext_id, NodeModel.id)
            .where(
                NodeModel.warehouse_id == warehouse_id,
                NodeModel.ext_id.in_(ext_ids),
            )
        )
        result = await self._session.execute(stmt)

        return {ext_id: node_id for ext_id, node_id in result.all()}

    async def get_ext_id_map_by_ids(self, warehouse_id: int, node_ids: set[int]) -> dict[int, int]:
        if not node_ids:
            return {}

        stmt = (
            select(NodeModel.id, NodeModel.ext_id)
            .where(
                NodeModel.warehouse_id == warehouse_id,
                NodeModel.id.in_(node_ids),
            )
        )
        res = await self._session.execute(stmt)
        return {node_id: ext_id for node_id, ext_id in res.all()}

    async def read_node(self, node_id: int) -> Optional[NodeModel]:
        stmt = select(NodeModel).where(NodeModel.id == node_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_nodes(self) -> Sequence[NodeModel]:
        stmt = select(NodeModel).order_by(NodeModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_nodes_by_warehouse(self, warehouse_id: int) -> Sequence[NodeModel]:
        stmt = (
            select(NodeModel)
            .where(NodeModel.warehouse_id == warehouse_id)
            .order_by(NodeModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_node(self, node: NodeModel) -> NodeModel:
        # merge полезен, если объект detached; вернёт инстанс, прикреплённый к session
        merged = await self._session.merge(node)

        # Flush отправляет UPDATE в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД
        await self._session.refresh(merged)
        return merged

    async def delete_node(self, node_id: int) -> bool:
        stmt = delete(NodeModel).where(NodeModel.id == node_id)
        result = await self._session.execute(stmt)

        # Flush фиксирует удаление в текущей транзакции (без commit).
        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_nodes_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(NodeModel).where(NodeModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)