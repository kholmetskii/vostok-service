from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositories.edge_repository import SQLAlchemyEdgeRepository
from app.infrastructure.db.repositories.node_repository import SQLAlchemyNodeRepository
from app.infrastructure.db.repositories.obstacle_repository import SQLAlchemyObstacleRepository
from app.infrastructure.db.repositories.shelf_repository import SQLAlchemyShelfRepository
from app.infrastructure.db.repositories.warehouse_repository import SQLAlchemyWarehouseRepository


@dataclass
class SQLAlchemyUnitOfWork:
    """
    Coordinate repositories within one SQLAlchemy transaction.

    Repository methods flush changes but never commit. Leaving the context commits
    on success or rolls back on any exception, then always closes the session.
    """

    session_factory: async_sessionmaker[AsyncSession]
    session: AsyncSession | None = None
    _tx = None
    warehouses: SQLAlchemyWarehouseRepository | None = None
    nodes: SQLAlchemyNodeRepository | None = None
    shelves: SQLAlchemyShelfRepository | None = None
    edges: SQLAlchemyEdgeRepository | None = None
    obstacles: SQLAlchemyObstacleRepository | None = None

    async def __aenter__(self) -> SQLAlchemyUnitOfWork:
        self.session = self.session_factory()
        self._tx = await self.session.begin()
        self.warehouses = SQLAlchemyWarehouseRepository(self.session)
        self.nodes = SQLAlchemyNodeRepository(self.session)
        self.shelves = SQLAlchemyShelfRepository(self.session)
        self.edges = SQLAlchemyEdgeRepository(self.session)
        self.obstacles = SQLAlchemyObstacleRepository(self.session)

        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            if self.session is not None:
                await self.session.close()

    async def commit(self) -> None:
        """Commit the active transaction."""
        if self._tx is not None:
            await self._tx.commit()
            self._tx = None

    async def rollback(self) -> None:
        """Roll back the active transaction."""
        if self._tx is not None:
            await self._tx.rollback()
            self._tx = None
