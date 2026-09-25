from __future__ import annotations

from collections.abc import Callable

from app.infrastructure.db.models.warehouse import WarehouseModel
from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


class WarehouseNotFound(Exception):
    """Raised when a warehouse ID does not exist."""


class WarehouseService:
    """Application service for warehouse CRUD operations."""

    def __init__(self, uow_factory: Callable[[], SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory

    async def create_warehouse(
        self,
        name: str,
        width_m: float,
        length_m: float,
        floor_count: int,
    ) -> WarehouseModel:
        """Create a warehouse and return its persisted model."""
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
        """Return all warehouses."""
        async with self._uow_factory() as uow:
            return list(await uow.warehouses.read_warehouses())

    async def get_warehouse(self, warehouse_id: int) -> WarehouseModel:
        """Return a warehouse or raise WarehouseNotFound."""
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")
            return warehouse

    async def delete_warehouse(self, warehouse_id: int) -> None:
        """Delete a warehouse or raise WarehouseNotFound."""
        async with self._uow_factory() as uow:
            deleted = await uow.warehouses.delete_warehouse(warehouse_id)
            if not deleted:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")
