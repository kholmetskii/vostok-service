from collections.abc import Iterable, Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.obstacle import ObstacleModel


class SQLAlchemyObstacleRepository:
    """Persist obstacles without owning the surrounding transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_obstacle(self, obstacle: ObstacleModel) -> ObstacleModel:
        self._session.add(obstacle)
        await self._session.flush()
        await self._session.refresh(obstacle)
        return obstacle

    async def create_obstacles_by_warehouse(
        self, obstacles: Iterable[dict], warehouse_id: int
    ) -> None:
        rows = [dict(o) for o in obstacles]
        if not rows:
            return

        for r in rows:
            r["warehouse_id"] = warehouse_id

        await self._session.execute(insert(ObstacleModel).values(rows))
        await self._session.flush()

    async def read_obstacle(self, obstacle_id: int) -> ObstacleModel | None:
        stmt = select(ObstacleModel).where(ObstacleModel.id == obstacle_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_obstacles(self) -> Sequence[ObstacleModel]:
        stmt = select(ObstacleModel).order_by(ObstacleModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def read_obstacles_by_warehouse(self, warehouse_id: int) -> Sequence[ObstacleModel]:
        stmt = (
            select(ObstacleModel)
            .where(ObstacleModel.warehouse_id == warehouse_id)
            .order_by(ObstacleModel.id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_obstacle(self, obstacle: ObstacleModel) -> ObstacleModel:
        merged = await self._session.merge(obstacle)
        await self._session.flush()
        await self._session.refresh(merged)
        return merged

    async def delete_obstacle(self, obstacle_id: int) -> bool:
        stmt = delete(ObstacleModel).where(ObstacleModel.id == obstacle_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_obstacles_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(ObstacleModel).where(ObstacleModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)
