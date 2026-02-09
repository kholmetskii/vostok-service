from typing import Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.warehouse import WarehouseModel


class SQLAlchemyWarehouseRepository():
    """
    Репозиторий для Warehouse на Async SQLAlchemy.

    ВАЖНО:
    - Репозиторий НЕ делает commit/rollback.
    - Он работает в рамках внешней транзакции (Unit of Work / session.begin()).
    - Для того, чтобы INSERT/UPDATE/DELETE реально "попали" в текущую транзакцию,
      используем flush().

    Контракт методов:
    - create_warehouse: добавляет Warehouse в сессию, делает flush, возвращает объект (обычно уже с id).
    - read_warehouse: возвращает Warehouse или None, если не найдено.
    - read_warehouses: возвращает список всех складов.
    - update_warehouse: сохраняет изменения (через merge + flush) и возвращает прикреплённый объект.
    - delete_warehouse: удаляет запись и возвращает True, если удаление действительно произошло.
    """

    def __init__(self, session: AsyncSession):
        # AsyncSession обычно создаётся и управляется UnitOfWork
        self._session = session

    async def create_warehouse(self, warehouse: WarehouseModel) -> WarehouseModel:
        # Добавляем объект в сессию (в БД уйдёт после flush)
        self._session.add(warehouse)

        # Flush отправляет INSERT в текущую транзакцию, но НЕ делает commit.
        # После flush у объекта, как правило, уже будет заполнен id (если PK генерится БД).
        await self._session.flush()

        # Refresh опционален: нужен, если БД выставляет значения через server_default/trigger
        # и ты хочешь их сразу получить в объекте.
        await self._session.refresh(warehouse)
        return warehouse

    async def read_warehouse(self, warehouse_id: int) -> Optional[WarehouseModel]:
        stmt = select(WarehouseModel).where(WarehouseModel.id == warehouse_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def read_warehouses(self) -> Sequence[WarehouseModel]:
        stmt = select(WarehouseModel).order_by(WarehouseModel.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update_warehouse(self, warehouse: WarehouseModel) -> WarehouseModel:
        # merge полезен, если объект "detached" (не прикреплён к текущей сессии).
        # Возвращает инстанс, прикреплённый к session.
        merged = await self._session.merge(warehouse)

        # Flush отправляет UPDATE в текущую транзакцию, но НЕ делает commit.
        await self._session.flush()

        # Опционально: перечитать из БД (если есть триггеры/дефолты на стороне БД).
        await self._session.refresh(merged)
        return merged

    async def delete_warehouse(self, warehouse_id: int) -> bool:
        stmt = delete(WarehouseModel).where(WarehouseModel.id == warehouse_id)
        result = await self._session.execute(stmt)

        # Flush фиксирует удаление в текущей транзакции (без commit).
        await self._session.flush()

        # rowcount = сколько строк было удалено (может быть None в некоторых драйверах).
        return bool(result.rowcount or 0)