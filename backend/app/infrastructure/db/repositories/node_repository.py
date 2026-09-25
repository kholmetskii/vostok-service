from collections.abc import Iterable, Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.node import NodeModel


class SQLAlchemyNodeRepository:
    """Persist graph nodes without owning the surrounding transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_node(self, node: NodeModel) -> NodeModel:
        self._session.add(node)
        await self._session.flush()
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

        stmt = select(NodeModel.ext_id, NodeModel.id).where(
            NodeModel.warehouse_id == warehouse_id,
            NodeModel.ext_id.in_(ext_ids),
        )
        result = await self._session.execute(stmt)

        return {ext_id: node_id for ext_id, node_id in result.all()}

    async def get_ext_id_map_by_ids(self, warehouse_id: int, node_ids: set[int]) -> dict[int, int]:
        if not node_ids:
            return {}

        stmt = select(NodeModel.id, NodeModel.ext_id).where(
            NodeModel.warehouse_id == warehouse_id,
            NodeModel.id.in_(node_ids),
        )
        res = await self._session.execute(stmt)
        return {node_id: ext_id for node_id, ext_id in res.all()}

    async def read_node(self, node_id: int) -> NodeModel | None:
        stmt = select(NodeModel).where(NodeModel.id == node_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_nodes(self) -> Sequence[NodeModel]:
        stmt = select(NodeModel).order_by(NodeModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_nodes_by_warehouse(self, warehouse_id: int) -> Sequence[NodeModel]:
        stmt = (
            select(NodeModel).where(NodeModel.warehouse_id == warehouse_id).order_by(NodeModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_node(self, node: NodeModel) -> NodeModel:
        merged = await self._session.merge(node)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_node(self, node_id: int) -> bool:
        stmt = delete(NodeModel).where(NodeModel.id == node_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_nodes_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(NodeModel).where(NodeModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)
