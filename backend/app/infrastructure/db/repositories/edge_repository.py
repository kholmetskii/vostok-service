from collections.abc import Iterable, Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.edge import EdgeModel


class SQLAlchemyEdgeRepository:
    """Persist edges without owning the surrounding transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_edge(self, edge: EdgeModel) -> EdgeModel:
        self._session.add(edge)
        await self._session.flush()
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

    async def read_edge(self, edge_id: int) -> EdgeModel | None:
        stmt = select(EdgeModel).where(EdgeModel.id == edge_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_edges(self) -> Sequence[EdgeModel]:
        stmt = select(EdgeModel).order_by(EdgeModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_edges_by_warehouse(self, warehouse_id: int) -> Sequence[EdgeModel]:
        stmt = (
            select(EdgeModel).where(EdgeModel.warehouse_id == warehouse_id).order_by(EdgeModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_edge(self, edge: EdgeModel) -> EdgeModel:
        merged = await self._session.merge(edge)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_edge(self, edge_id: int) -> bool:
        stmt = delete(EdgeModel).where(EdgeModel.id == edge_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_edges_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(EdgeModel).where(EdgeModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)
