from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


class ConfigValidationError(Exception):
    """Конфигурация некорректна (инварианты/ссылки/геометрия/формат)."""
    pass


def _ensure_int(value: Any, field: str) -> int:
    """Приводим к int и даём понятную ошибку."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConfigValidationError(f"Field '{field}' must be int, got: {value!r}")


def _ensure_float(value: Any, field: str) -> float:
    """Приводим к float и даём понятную ошибку."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ConfigValidationError(f"Field '{field}' must be float, got: {value!r}")


def _ensure_unique_ext_ids(items: Iterable[dict], entity: str) -> None:
    """Проверяем уникальность ext_id внутри одного листа (nodes/shelves/edges/obstacles)."""
    seen: set[int] = set()
    dup: set[int] = set()

    for obj in items:
        ext_id = _ensure_int(obj.get("ext_id"), f"{entity}.ext_id")
        if ext_id in seen:
            dup.add(ext_id)
        seen.add(ext_id)

    if dup:
        raise ConfigValidationError(f"Duplicate ext_id in '{entity}': {sorted(dup)}")


@dataclass(frozen=True)
class PreparedWarehouseConfig:
    """
    Подготовленные структуры для bulk insert (после конвертации ext_id -> id).
    """
    shelves_rows: list[dict]
    edges_rows: list[dict]
    obstacles_rows: list[dict]


class WarehouseConfigValidator:
    """
    Валидатор/нормализатор payload конфигурации склада.

    Что проверяет:
    1) Структура payload (nodes/shelves/edges/obstacles должны быть lists)
    2) Уникальность ext_id в каждом списке
    3) Ссылочная целостность по node_ext_id/from_node_ext_id/to_node_ext_id (внутри payload.nodes)
    4) Геометрия (top-left coords): объекты должны быть в пределах склада
    5) floor_level ∈ [0..floor_count-1] для nodes/shelves

    Два этапа:
    - validate(payload, warehouse_*) -> возвращает needed_node_ext_ids (для get_id_map_by_ext_ids)
    - prepare_rows(payload, id_map, nodes_floor_by_ext_id=...) -> конвертация ext->id
    """

    def validate(
        self,
        payload: dict,
        *,
        warehouse_width_m: float,
        warehouse_length_m: float,
        warehouse_floor_count: int,
        require_same_floor_for_links: bool = True,
    ) -> set[int]:
        nodes = payload.get("nodes", [])
        shelves = payload.get("shelves", [])
        edges = payload.get("edges", [])
        obstacles = payload.get("obstacles", [])

        # --- 1) базовые проверки структуры ---
        if not all(isinstance(x, list) for x in (nodes, shelves, edges, obstacles)):
            raise ConfigValidationError("Payload fields nodes/shelves/edges/obstacles must be lists")

        # --- 2) уникальность ext_id ---
        _ensure_unique_ext_ids(nodes, "nodes")
        _ensure_unique_ext_ids(shelves, "shelves")
        _ensure_unique_ext_ids(edges, "edges")
        _ensure_unique_ext_ids(obstacles, "obstacles")

        # --- 3) размеры склада ---
        W = float(warehouse_width_m)
        L = float(warehouse_length_m)
        floors = _ensure_int(warehouse_floor_count, "warehouse.floor_count")

        if W <= 0 or L <= 0:
            raise ConfigValidationError("Warehouse dimensions must be positive")
        if floors <= 0:
            raise ConfigValidationError("warehouse.floor_count must be positive")

        # --- 4) собрать node_ext_ids из payload + floor_level map ---
        node_ext_ids_in_payload: set[int] = set()
        nodes_floor_by_ext: dict[int, int] = {}

        for n in nodes:
            ext_id = _ensure_int(n.get("ext_id"), "nodes.ext_id")
            floor_level = _ensure_int(n.get("floor_level"), f"nodes[{ext_id}].floor_level")

            if not (1 <= floor_level <= floors):
                raise ConfigValidationError(
                    f"Node ext_id={ext_id} has invalid floor_level={floor_level}. Expected in [1..{floors }]"
                )

            x = _ensure_float(n.get("x_m"), f"nodes[{ext_id}].x_m")
            y = _ensure_float(n.get("y_m"), f"nodes[{ext_id}].y_m")

            # top-left coords: 0..W по x, 0..L по y
            if x < 0.0 or y < 0.0 or x > W or y > L:
                raise ConfigValidationError(
                    f"Node ext_id={ext_id} out of warehouse bounds: "
                    f"(x_m={x}, y_m={y}) not in [0..{W}]x[0..{L}] (top-left coords)"
                )

            node_ext_ids_in_payload.add(ext_id)
            nodes_floor_by_ext[ext_id] = floor_level

        # --- 5) shelves геометрия + ссылки ---
        needed_ext_ids: set[int] = set()

        for s in shelves:
            ext_id = _ensure_int(s.get("ext_id"), "shelves.ext_id")

            floor_level = _ensure_int(s.get("floor_level"), f"shelves[{ext_id}].floor_level")
            if not (1 <= floor_level <= floors):
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} has invalid floor_level={floor_level}. Expected in [1..{floors}]"
                )

            x = _ensure_float(s.get("x_m"), f"shelves[{ext_id}].x_m")
            y = _ensure_float(s.get("y_m"), f"shelves[{ext_id}].y_m")
            width = _ensure_float(s.get("width_m"), f"shelves[{ext_id}].width_m")
            length = _ensure_float(s.get("length_m"), f"shelves[{ext_id}].length_m")

            if width <= 0.0 or length <= 0.0:
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} has non-positive size: width_m={width}, length_m={length}"
                )

            # top-left shelf: bottom-right (x+width, y+length) must fit
            if x < 0.0 or y < 0.0 or (x + width) > W or (y + length) > L:
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} out of warehouse bounds: "
                    f"top-left=({x},{y}), size=({width},{length}) => "
                    f"bottom-right=({x + width},{y + length}) not in [0..{W}]x[0..{L}]"
                )

            node_ext = _ensure_int(s.get("node_ext_id"), f"shelves[{ext_id}].node_ext_id")
            needed_ext_ids.add(node_ext)

        # --- 6) edges/obstacles ссылки + from!=to (+ этажность по узлам) ---
        def _validate_link(entity: str, obj: dict) -> tuple[int, int, int]:
            ext_id = _ensure_int(obj.get("ext_id"), f"{entity}.ext_id")
            from_ext = _ensure_int(obj.get("from_node_ext_id"), f"{entity}[{ext_id}].from_node_ext_id")
            to_ext = _ensure_int(obj.get("to_node_ext_id"), f"{entity}[{ext_id}].to_node_ext_id")
            if from_ext == to_ext:
                raise ConfigValidationError(f"{entity} ext_id={ext_id} must have different from_node_ext_id and to_node_ext_id")
            return ext_id, from_ext, to_ext

        for e in edges:
            _, from_ext, to_ext = _validate_link("edges", e)
            needed_ext_ids.add(from_ext)
            needed_ext_ids.add(to_ext)

        for o in obstacles:
            _, from_ext, to_ext = _validate_link("obstacles", o)
            needed_ext_ids.add(from_ext)
            needed_ext_ids.add(to_ext)

        # --- 7) ссылки должны указывать на nodes из payload (Excel source of truth) ---
        missing_in_payload = needed_ext_ids - node_ext_ids_in_payload
        if missing_in_payload:
            raise ConfigValidationError(
                f"Config references unknown node ext_id (not present in payload.nodes): {sorted(missing_in_payload)}"
            )


        return needed_ext_ids

    def prepare_rows(
        self,
        payload: dict,
        *,
        id_map: dict[int, int],
    ) -> PreparedWarehouseConfig:
        """
        Конвертирует ссылки ext_id -> id в shelves/edges/obstacles.

        Предполагается, что validate(...) уже вызывали.
        Но дополнительно проверяем, что id_map покрывает все ссылки.
        """
        shelves = payload.get("shelves", [])
        edges = payload.get("edges", [])
        obstacles = payload.get("obstacles", [])

        # собрать все нужные ext_id для FK, чтобы проверить покрытие id_map
        needed_ext_ids: set[int] = set()
        for s in shelves:
            needed_ext_ids.add(_ensure_int(s.get("node_ext_id"), "shelves.node_ext_id"))
        for e in edges:
            needed_ext_ids.add(_ensure_int(e.get("from_node_ext_id"), "edges.from_node_ext_id"))
            needed_ext_ids.add(_ensure_int(e.get("to_node_ext_id"), "edges.to_node_ext_id"))
        for o in obstacles:
            needed_ext_ids.add(_ensure_int(o.get("from_node_ext_id"), "obstacles.from_node_ext_id"))
            needed_ext_ids.add(_ensure_int(o.get("to_node_ext_id"), "obstacles.to_node_ext_id"))

        missing = needed_ext_ids - set(id_map.keys())
        if missing:
            raise ConfigValidationError(f"Unknown node ext_id referenced (no DB mapping): {sorted(missing)}")

        # --- shelves rows ---
        shelves_rows: list[dict] = []
        for s in shelves:
            row = dict(s)
            node_ext = _ensure_int(row.pop("node_ext_id"), "shelves.node_ext_id")
            row["node_id"] = id_map[node_ext]
            shelves_rows.append(row)

        # --- edges rows ---
        edges_rows: list[dict] = []
        for e in edges:
            row = dict(e)
            from_ext = _ensure_int(row.pop("from_node_ext_id"), "edges.from_node_ext_id")
            to_ext = _ensure_int(row.pop("to_node_ext_id"), "edges.to_node_ext_id")
            row["from_node_id"] = id_map[from_ext]
            row["to_node_id"] = id_map[to_ext]
            edges_rows.append(row)

        # --- obstacles rows ---
        obstacles_rows: list[dict] = []
        for o in obstacles:
            row = dict(o)
            from_ext = _ensure_int(row.pop("from_node_ext_id"), "obstacles.from_node_ext_id")
            to_ext = _ensure_int(row.pop("to_node_ext_id"), "obstacles.to_node_ext_id")
            row["from_node_id"] = id_map[from_ext]
            row["to_node_id"] = id_map[to_ext]
            obstacles_rows.append(row)

        return PreparedWarehouseConfig(
            shelves_rows=shelves_rows,
            edges_rows=edges_rows,
            obstacles_rows=obstacles_rows,
        )