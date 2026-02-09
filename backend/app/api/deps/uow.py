from __future__ import annotations

from collections.abc import Callable
from app.infrastructure.db.session import SessionFactory
from app.infrastructure.db.uow import SQLAlchemyUnitOfWork

def get_uow_factory() -> Callable[[], SQLAlchemyUnitOfWork]:
    # Фабрика нужна, чтобы use-case сам создавал UoW (и сам делал async with uow)
    return lambda: SQLAlchemyUnitOfWork(SessionFactory)