from __future__ import annotations

from collections.abc import Callable

from app.infrastructure.db.uow import SQLAlchemyUnitOfWork
from app.infrastructure.db.models.warehouse import WarehouseModel


class WarehouseNotFound(Exception):
    """Warehouse с указанным id не найден."""
    pass


class WarehouseService:
    """
    Application service для CRUD по Warehouse.

    Содержит сценарии:
    - create_warehouse
    - list_warehouses
    - get_warehouse
    - delete_warehouse
    """

    def __init__(self, uow_factory: Callable[[], SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory

    async def create_warehouse(
        self,
        name: str,
        width_m: float,
        length_m: float,
        floor_count: int,
    ) -> WarehouseModel:
        """
        Создаёт warehouse и возвращает ORM-модель (WarehouseModel).

        ВАЖНО:
        - commit произойдёт автоматически при выходе из async with, если не было исключений.
        - repo.create_warehouse должен делать add + flush (без commit).
        """
        async with self._uow_factory() as uow:
            warehouse = WarehouseModel(
                name=name,
                width_m=width_m,
                length_m=length_m,
                floor_count=floor_count,
            )
            created = await uow.warehouses.create_warehouse(warehouse)
            return created

    async def list_warehouses(self) -> list[WarehouseModel]:
        """Возвращает список всех складов."""
        async with self._uow_factory() as uow:
            return list(await uow.warehouses.read_warehouses())

    async def get_warehouse(self, warehouse_id: int) -> WarehouseModel:
        """Возвращает warehouse по id или кидает WarehouseNotFound."""
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")
            return warehouse

    async def delete_warehouse(self, warehouse_id: int) -> None:
        """
        Удаляет warehouse по id.

        Если warehouse не найден — кидает WarehouseNotFound.
        """
        async with self._uow_factory() as uow:
            deleted = await uow.warehouses.delete_warehouse(warehouse_id)
            if not deleted:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")