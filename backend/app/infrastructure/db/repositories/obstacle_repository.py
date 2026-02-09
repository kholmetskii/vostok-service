from typing import Optional, Sequence, Iterable

from sqlalchemy import delete, select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.obstacle import ObstacleModel


class SQLAlchemyObstacleRepository:
    """
    Репозиторий для Obstacle на Async SQLAlchemy.

    ВАЖНО:
    - Репозиторий НЕ делает commit/rollback.
    - Он работает в рамках внешней транзакции (UnitOfWork / session.begin()).
    - Для применения изменений в текущей транзакции используем flush().

    Контракт методов:
    - create_obstacle: добавляет Obstacle в сессию, делает flush, возвращает объект (обычно уже с id).
    - read_obstacle: возвращает Obstacle или None, если не найдено.
    - read_obstacles: возвращает список всех препятствий.
    - read_obstacles_by_warehouse: возвращает список препятствий конкретного склада.
    - update_obstacle: сохраняет изменения (через merge + flush) и возвращает прикреплённый объект.
    - delete_obstacle: возвращает True, если запись удалена, иначе False.
    - delete_obstacles_by_warehouse: удаляет препятствия склада, возвращает True если удалено хотя бы что-то.
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession обычно создаётся и управляется UnitOfWork
        self._session = session

    async def create_obstacle(self, obstacle: ObstacleModel) -> ObstacleModel:
        # Добавляем объект в сессию (в БД уйдёт после flush)
        self._session.add(obstacle)

        # Flush отправляет INSERT в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД (server_default/trigger и т.п.)
        await self._session.refresh(obstacle)
        return obstacle

    async def create_obstacles_by_warehouse(self, obstacles: Iterable[dict], warehouse_id: int) -> None:
        rows = [dict(o) for o in obstacles]
        if not rows:
            return

        for r in rows:
            r["warehouse_id"] = warehouse_id

        await self._session.execute(insert(ObstacleModel).values(rows))
        await self._session.flush()

    async def read_obstacle(self, obstacle_id: int) -> Optional[ObstacleModel]:
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
        # merge полезен, если объект detached; вернёт инстанс, прикреплённый к session
        merged = await self._session.merge(obstacle)

        # Flush отправляет UPDATE в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать поля из БД
        await self._session.refresh(merged)
        return merged

    async def delete_obstacle(self, obstacle_id: int) -> bool:
        stmt = delete(ObstacleModel).where(ObstacleModel.id == obstacle_id)
        result = await self._session.execute(stmt)

        # Flush фиксирует удаление в текущей транзакции (без commit).
        await self._session.flush()
        return bool(result.rowcount or 0)

    async def delete_obstacles_by_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(ObstacleModel).where(ObstacleModel.warehouse_id == warehouse_id)
        result = await self._session.execute(stmt)

        await self._session.flush()
        return bool(result.rowcount or 0)