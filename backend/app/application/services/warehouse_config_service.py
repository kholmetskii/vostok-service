from __future__ import annotations

from collections.abc import Callable

from app.infrastructure.db.uow import SQLAlchemyUnitOfWork
from app.application.validators.warehouse_config_validator import (
    WarehouseConfigValidator,
    ConfigValidationError,
)


class WarehouseNotFound(Exception):
    """Warehouse с указанным id не найден."""
    pass


class WarehouseConfigService:
    """
    Application service: работа с конфигурацией склада (Excel = source of truth).
    """

    def __init__(self, uow_factory: Callable[[], SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory
        self._validator = WarehouseConfigValidator()

    async def replace_config(self, warehouse_id: int, payload: dict) -> None:
        async with self._uow_factory() as uow:
            # 1) Warehouse должен существовать (и нужны его размеры/этажи для гео-валидации)
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            # 2) Валидация payload (структура/уникальность/ссылки/геометрия/этажи)
            needed_ext_ids = self._validator.validate(
                payload,
                warehouse_width_m=warehouse.width_m,
                warehouse_length_m=warehouse.length_m,
                warehouse_floor_count=warehouse.floor_count,
                require_same_floor_for_links=True,  # edges/obstacles должны связывать nodes на одном этаже
            )

            nodes = payload.get("nodes", [])
            shelves = payload.get("shelves", [])
            edges = payload.get("edges", [])
            obstacles = payload.get("obstacles", [])

            # 3) Удаляем старое (Excel = source of truth)
            await uow.edges.delete_edges_by_warehouse(warehouse_id)
            await uow.obstacles.delete_obstacles_by_warehouse(warehouse_id)
            await uow.shelves.delete_shelves_by_warehouse(warehouse_id)
            await uow.nodes.delete_nodes_by_warehouse(warehouse_id)

            # 4) Вставляем nodes (после этого можем получить id_map ext_id -> id)
            await uow.nodes.create_nodes_by_warehouse(nodes, warehouse_id)

            # 5) Маппинг ext_id -> id (по нужным ext_id, которые реально используются в FK)
            id_map = await uow.nodes.get_id_map_by_ext_ids(warehouse_id, needed_ext_ids)

            # 6) Подготовка rows (конвертация *_ext_id -> *_id + финальная проверка покрытия id_map)
            prepared = self._validator.prepare_rows(payload, id_map=id_map)

            # 7) Bulk insert остального
            await uow.shelves.create_shelves_by_warehouse(prepared.shelves_rows, warehouse_id)
            await uow.edges.create_edges_by_warehouse(prepared.edges_rows, warehouse_id)
            await uow.obstacles.create_obstacles_by_warehouse(prepared.obstacles_rows, warehouse_id)

            # commit произойдёт автоматически при выходе из async with

    async def get_config(self, warehouse_id: int) -> dict:
        """
        Возвращает конфигурацию в формате WarehouseConfigOut (с *_ext_id ссылками).
        Предполагается, что get_config ты уже переписал под ext_id-based output.
        """
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            nodes = await uow.nodes.read_nodes_by_warehouse(warehouse_id)
            shelves = await uow.shelves.read_shelves_by_warehouse(warehouse_id)
            edges = await uow.edges.read_edges_by_warehouse(warehouse_id)
            obstacles = await uow.obstacles.read_obstacles_by_warehouse(warehouse_id)

            # node_id -> ext_id map (оптимизацию через get_ext_id_map_by_ids ты уже делал выше)
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