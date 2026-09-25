from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


class ConfigValidationError(Exception):
    """Raised when a warehouse configuration violates its data contract."""


def _ensure_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ConfigValidationError(f"Field '{field}' must be int, got: {value!r}") from None


def _ensure_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ConfigValidationError(f"Field '{field}' must be float, got: {value!r}") from None


def _ensure_unique_ext_ids(items: Iterable[dict], entity: str) -> None:
    """Require unique external IDs within one entity collection."""
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
    """Rows prepared for bulk insertion after resolving external node IDs."""

    shelves_rows: list[dict]
    edges_rows: list[dict]
    obstacles_rows: list[dict]


class WarehouseConfigValidator:
    """
    Validate and prepare a complete warehouse configuration.

    Validation covers collection structure, unique external IDs, node references,
    one-based floor levels, and warehouse bounds. Edges may connect nodes on
    different floors; planar obstacles are interpreted by the routing service.
    """

    def validate(
        self,
        payload: dict,
        *,
        warehouse_width_m: float,
        warehouse_length_m: float,
        warehouse_floor_count: int,
    ) -> set[int]:
        nodes = payload.get("nodes", [])
        shelves = payload.get("shelves", [])
        edges = payload.get("edges", [])
        obstacles = payload.get("obstacles", [])

        if not all(isinstance(x, list) for x in (nodes, shelves, edges, obstacles)):
            raise ConfigValidationError(
                "Payload fields nodes/shelves/edges/obstacles must be lists"
            )

        _ensure_unique_ext_ids(nodes, "nodes")
        _ensure_unique_ext_ids(shelves, "shelves")
        _ensure_unique_ext_ids(edges, "edges")
        _ensure_unique_ext_ids(obstacles, "obstacles")

        width_m = float(warehouse_width_m)
        length_m = float(warehouse_length_m)
        floors = _ensure_int(warehouse_floor_count, "warehouse.floor_count")

        if width_m <= 0 or length_m <= 0:
            raise ConfigValidationError("Warehouse dimensions must be positive")
        if floors <= 0:
            raise ConfigValidationError("warehouse.floor_count must be positive")

        node_ext_ids_in_payload: set[int] = set()

        for n in nodes:
            ext_id = _ensure_int(n.get("ext_id"), "nodes.ext_id")
            floor_level = _ensure_int(n.get("floor_level"), f"nodes[{ext_id}].floor_level")

            if not (1 <= floor_level <= floors):
                raise ConfigValidationError(
                    f"Node ext_id={ext_id} has invalid floor_level={floor_level}. "
                    f"Expected in [1..{floors}]"
                )

            x = _ensure_float(n.get("x_m"), f"nodes[{ext_id}].x_m")
            y = _ensure_float(n.get("y_m"), f"nodes[{ext_id}].y_m")

            if x < 0.0 or y < 0.0 or x > width_m or y > length_m:
                raise ConfigValidationError(
                    f"Node ext_id={ext_id} out of warehouse bounds: "
                    f"(x_m={x}, y_m={y}) not in [0..{width_m}]x[0..{length_m}] "
                    "(top-left coordinates)"
                )

            node_ext_ids_in_payload.add(ext_id)

        needed_ext_ids: set[int] = set()

        for s in shelves:
            ext_id = _ensure_int(s.get("ext_id"), "shelves.ext_id")

            floor_level = _ensure_int(s.get("floor_level"), f"shelves[{ext_id}].floor_level")
            if not (1 <= floor_level <= floors):
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} has invalid floor_level={floor_level}. "
                    f"Expected in [1..{floors}]"
                )

            x = _ensure_float(s.get("x_m"), f"shelves[{ext_id}].x_m")
            y = _ensure_float(s.get("y_m"), f"shelves[{ext_id}].y_m")
            width = _ensure_float(s.get("width_m"), f"shelves[{ext_id}].width_m")
            length = _ensure_float(s.get("length_m"), f"shelves[{ext_id}].length_m")

            if width <= 0.0 or length <= 0.0:
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} has non-positive size: "
                    f"width_m={width}, length_m={length}"
                )

            if x < 0.0 or y < 0.0 or (x + width) > width_m or (y + length) > length_m:
                raise ConfigValidationError(
                    f"Shelf ext_id={ext_id} out of warehouse bounds: "
                    f"top-left=({x},{y}), size=({width},{length}) => "
                    f"bottom-right=({x + width},{y + length}) not in "
                    f"[0..{width_m}]x[0..{length_m}]"
                )

            node_ext = _ensure_int(s.get("node_ext_id"), f"shelves[{ext_id}].node_ext_id")
            needed_ext_ids.add(node_ext)

        def _validate_link(entity: str, obj: dict) -> tuple[int, int, int]:
            ext_id = _ensure_int(obj.get("ext_id"), f"{entity}.ext_id")
            from_ext = _ensure_int(
                obj.get("from_node_ext_id"), f"{entity}[{ext_id}].from_node_ext_id"
            )
            to_ext = _ensure_int(obj.get("to_node_ext_id"), f"{entity}[{ext_id}].to_node_ext_id")
            if from_ext == to_ext:
                raise ConfigValidationError(
                    f"{entity} ext_id={ext_id} must have different "
                    "from_node_ext_id and to_node_ext_id"
                )
            return ext_id, from_ext, to_ext

        for e in edges:
            _, from_ext, to_ext = _validate_link("edges", e)
            needed_ext_ids.add(from_ext)
            needed_ext_ids.add(to_ext)

        for o in obstacles:
            _, from_ext, to_ext = _validate_link("obstacles", o)
            needed_ext_ids.add(from_ext)
            needed_ext_ids.add(to_ext)

        missing_in_payload = needed_ext_ids - node_ext_ids_in_payload
        if missing_in_payload:
            raise ConfigValidationError(
                "Config references unknown node ext_id (not present in payload.nodes): "
                f"{sorted(missing_in_payload)}"
            )
        return needed_ext_ids

    def prepare_rows(
        self,
        payload: dict,
        *,
        id_map: dict[int, int],
    ) -> PreparedWarehouseConfig:
        """Resolve external node references and return database-ready rows."""
        shelves = payload.get("shelves", [])
        edges = payload.get("edges", [])
        obstacles = payload.get("obstacles", [])

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
            raise ConfigValidationError(
                f"Unknown node ext_id referenced (no DB mapping): {sorted(missing)}"
            )

        shelves_rows: list[dict] = []
        for s in shelves:
            row = dict(s)
            node_ext = _ensure_int(row.pop("node_ext_id"), "shelves.node_ext_id")
            row["node_id"] = id_map[node_ext]
            shelves_rows.append(row)

        edges_rows: list[dict] = []
        for e in edges:
            row = dict(e)
            from_ext = _ensure_int(row.pop("from_node_ext_id"), "edges.from_node_ext_id")
            to_ext = _ensure_int(row.pop("to_node_ext_id"), "edges.to_node_ext_id")
            row["from_node_id"] = id_map[from_ext]
            row["to_node_id"] = id_map[to_ext]
            edges_rows.append(row)

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
