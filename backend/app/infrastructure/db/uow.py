from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.warehouse_repository import SQLAlchemyWarehouseRepository
from app.infrastructure.db.repositories.node_repository import SQLAlchemyNodeRepository
from app.infrastructure.db.repositories.shelf_repository import SQLAlchemyShelfRepository
from app.infrastructure.db.repositories.edge_repository import SQLAlchemyEdgeRepository
from app.infrastructure.db.repositories.obstacle_repository import SQLAlchemyObstacleRepository


@dataclass
class SQLAlchemyUnitOfWork:
    """
    Unit of Work (UoW) для Async SQLAlchemy.

    Зачем нужен:
    - Гарантирует "одна бизнес-операция = одна транзакция".
    - Собирает репозитории, которые работают в рамках одной и той же AsyncSession.
    - Управляет commit/rollback централизованно (репозитории commit НЕ делают).

    Как использовать:
        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            await uow.nodes.upsert_many(...)
            await uow.shelves.delete_shelves_by_warehouse(...)
            ...
        # при выходе из блока:
        # - если ошибок не было -> commit
        # - если было исключение -> rollback
    """

    # Фабрика сессий (обычно async_sessionmaker, созданный от engine)
    session_factory: async_sessionmaker[AsyncSession]

    # Текущая сессия UoW. Создаётся при входе в async with, закрывается при выходе.
    session: AsyncSession | None = None

    # Объект транзакции, который возвращает session.begin().
    # Храним его, чтобы явно сделать commit/rollback.
    _tx = None

    # Репозитории, привязанные к текущей session (инициализируются в __aenter__)
    warehouses: SQLAlchemyWarehouseRepository | None = None
    nodes: SQLAlchemyNodeRepository | None = None
    shelves: SQLAlchemyShelfRepository | None = None
    edges: SQLAlchemyEdgeRepository | None = None
    obstacles: SQLAlchemyObstacleRepository | None = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        # 1) Создаём новую AsyncSession для текущей бизнес-операции
        self.session = self.session_factory()

        # 2) Открываем транзакцию
        # Важно: репозитории внутри UoW будут делать только flush(),
        # а commit/rollback будет происходить здесь.
        self._tx = await self.session.begin()

        # 3) Создаём репозитории, все они используют ОДНУ и ту же session
        self.warehouses = SQLAlchemyWarehouseRepository(self.session)
        self.nodes = SQLAlchemyNodeRepository(self.session)
        self.shelves = SQLAlchemyShelfRepository(self.session)
        self.edges = SQLAlchemyEdgeRepository(self.session)
        self.obstacles = SQLAlchemyObstacleRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        """
        При выходе из async with:
        - если ошибок нет (exc is None) -> commit
        - если было исключение -> rollback
        В конце всегда закрываем session, чтобы не было утечек соединений.
        """
        try:
            if exc is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            if self.session is not None:
                await self.session.close()

    async def commit(self) -> None:
        """
        Фиксируем транзакцию.
        Вызывается автоматически в __aexit__, если внутри блока не было исключений.
        """
        if self._tx is not None:
            await self._tx.commit()
            self._tx = None

    async def rollback(self) -> None:
        """
        Откатываем транзакцию.
        Вызывается автоматически в __aexit__, если внутри блока было исключение.
        """
        if self._tx is not None:
            await self._tx.rollback()
            self._tx = None