from __future__ import annotations

from collections.abc import Callable

from app.application.validators.warehouse_config_validator import (
    WarehouseConfigValidator,
)
from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


class WarehouseNotFound(Exception):
    """Raised when a warehouse ID does not exist."""


class WarehouseConfigService:
    """Replace and retrieve warehouse configurations as a single transaction."""

    def __init__(self, uow_factory: Callable[[], SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory
        self._validator = WarehouseConfigValidator()

    async def replace_config(self, warehouse_id: int, payload: dict) -> None:
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            needed_ext_ids = self._validator.validate(
                payload,
                warehouse_width_m=warehouse.width_m,
                warehouse_length_m=warehouse.length_m,
                warehouse_floor_count=warehouse.floor_count,
            )

            nodes = payload.get("nodes", [])

            # The uploaded workbook is the source of truth for the full configuration.
            await uow.edges.delete_edges_by_warehouse(warehouse_id)
            await uow.obstacles.delete_obstacles_by_warehouse(warehouse_id)
            await uow.shelves.delete_shelves_by_warehouse(warehouse_id)
            await uow.nodes.delete_nodes_by_warehouse(warehouse_id)

            await uow.nodes.create_nodes_by_warehouse(nodes, warehouse_id)

            id_map = await uow.nodes.get_id_map_by_ext_ids(warehouse_id, needed_ext_ids)

            prepared = self._validator.prepare_rows(payload, id_map=id_map)

            await uow.shelves.create_shelves_by_warehouse(prepared.shelves_rows, warehouse_id)
            await uow.edges.create_edges_by_warehouse(prepared.edges_rows, warehouse_id)
            await uow.obstacles.create_obstacles_by_warehouse(prepared.obstacles_rows, warehouse_id)

    async def get_config(self, warehouse_id: int) -> dict:
        """Return a configuration using external node IDs in public references."""
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            nodes = await uow.nodes.read_nodes_by_warehouse(warehouse_id)
            shelves = await uow.shelves.read_shelves_by_warehouse(warehouse_id)
            edges = await uow.edges.read_edges_by_warehouse(warehouse_id)
            obstacles = await uow.obstacles.read_obstacles_by_warehouse(warehouse_id)

            node_ext_by_id = {n.id: n.ext_id for n in nodes}

            return {
                "warehouse": warehouse,
                "nodes": [
                    {"ext_id": n.ext_id, "floor_level": n.floor_level, "x_m": n.x_m, "y_m": n.y_m}
                    for n in nodes
                ],
                "shelves": [
                    {
                        "ext_id": s.ext_id,
                        "floor_level": s.floor_level,
                        "x_m": s.x_m,
                        "y_m": s.y_m,
                        "width_m": s.width_m,
                        "length_m": s.length_m,
                        "shelving_code": s.shelving_code,
                        "section_code": s.section_code,
                        "node_ext_id": node_ext_by_id.get(s.node_id),
                    }
                    for s in shelves
                ],
                "edges": [
                    {
                        "ext_id": e.ext_id,
                        "from_node_ext_id": node_ext_by_id.get(e.from_node_id),
                        "to_node_ext_id": node_ext_by_id.get(e.to_node_id),
                        "weight_multiplier": e.weight_multiplier,
                    }
                    for e in edges
                ],
                "obstacles": [
                    {
                        "ext_id": o.ext_id,
                        "from_node_ext_id": node_ext_by_id.get(o.from_node_id),
                        "to_node_ext_id": node_ext_by_id.get(o.to_node_id),
                    }
                    for o in obstacles
                ],
            }
