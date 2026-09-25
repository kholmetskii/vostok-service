from __future__ import annotations

from collections.abc import Callable

from app.infrastructure.db.session import SessionFactory
from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


def get_uow_factory() -> Callable[[], SQLAlchemyUnitOfWork]:
    """Return a fresh Unit of Work for each application-service operation."""
    return lambda: SQLAlchemyUnitOfWork(SessionFactory)
