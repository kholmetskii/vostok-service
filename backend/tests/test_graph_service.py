import asyncio
from types import SimpleNamespace

import pytest

from app.application.services.graph_service import GraphService, PathNotFound


def record(**values):
    return SimpleNamespace(**values)


class ShelfRepository:
    def __init__(self, shelves):
        self._shelves = {shelf.ext_id: shelf for shelf in shelves}

    async def read_shelf_by_ext_id(self, warehouse_id, shelf_ext_id):
        return self._shelves.get(shelf_ext_id)


class ListRepository:
    def __init__(self, values, method_name):
        self._values = values
        setattr(self, method_name, self._read)

    async def _read(self, warehouse_id):
        return self._values


class FakeUnitOfWork:
    def __init__(self, *, nodes, edges, obstacles, shelves):
        self.nodes = ListRepository(nodes, "read_nodes_by_warehouse")
        self.edges = ListRepository(edges, "read_edges_by_warehouse")
        self.obstacles = ListRepository(obstacles, "read_obstacles_by_warehouse")
        self.shelves = ShelfRepository(shelves)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


def run_route(*, nodes, edges, obstacles, start_node_id=1, goal_node_id=3):
    shelves = [
        record(ext_id=10, node_id=start_node_id),
        record(ext_id=20, node_id=goal_node_id),
    ]

    def factory():
        return FakeUnitOfWork(
            nodes=nodes,
            edges=edges,
            obstacles=obstacles,
            shelves=shelves,
        )

    return asyncio.run(GraphService(factory).find_path_between_shelves(1, 10, 20))


def test_shortest_path_uses_edge_weights():
    nodes = [
        record(id=1, ext_id=1, floor_level=1, x_m=0, y_m=0),
        record(id=2, ext_id=2, floor_level=1, x_m=1, y_m=0),
        record(id=3, ext_id=3, floor_level=1, x_m=2, y_m=0),
    ]
    edges = [
        record(ext_id=101, from_node_id=1, to_node_id=2, weight_multiplier=1),
        record(ext_id=102, from_node_id=2, to_node_id=3, weight_multiplier=1),
        record(ext_id=103, from_node_id=1, to_node_id=3, weight_multiplier=2),
    ]

    result = run_route(nodes=nodes, edges=edges, obstacles=[])

    assert result["distance_m"] == pytest.approx(2.0)
    assert [edge["ext_id"] for edge in result["path_edges"]] == [101, 102]


def test_unreachable_path_raises_when_an_obstacle_blocks_the_only_edge():
    nodes = [
        record(id=1, ext_id=1, floor_level=1, x_m=0, y_m=0),
        record(id=2, ext_id=2, floor_level=1, x_m=1, y_m=-1),
        record(id=3, ext_id=3, floor_level=1, x_m=2, y_m=0),
        record(id=4, ext_id=4, floor_level=1, x_m=1, y_m=1),
    ]
    edges = [record(ext_id=101, from_node_id=1, to_node_id=3, weight_multiplier=1)]
    obstacles = [record(ext_id=201, from_node_id=2, to_node_id=4)]

    with pytest.raises(PathNotFound, match="No path"):
        run_route(nodes=nodes, edges=edges, obstacles=obstacles)


def test_dynamic_obstacle_changes_the_selected_route():
    nodes = [
        record(id=1, ext_id=1, floor_level=1, x_m=0, y_m=0),
        record(id=2, ext_id=2, floor_level=1, x_m=1, y_m=-1),
        record(id=3, ext_id=3, floor_level=1, x_m=2, y_m=0),
        record(id=4, ext_id=4, floor_level=1, x_m=0, y_m=2),
        record(id=5, ext_id=5, floor_level=1, x_m=2, y_m=2),
        record(id=6, ext_id=6, floor_level=1, x_m=1, y_m=1),
    ]
    edges = [
        record(ext_id=101, from_node_id=1, to_node_id=3, weight_multiplier=1),
        record(ext_id=102, from_node_id=1, to_node_id=4, weight_multiplier=1),
        record(ext_id=103, from_node_id=4, to_node_id=5, weight_multiplier=1),
        record(ext_id=104, from_node_id=5, to_node_id=3, weight_multiplier=1),
    ]

    direct = run_route(nodes=nodes, edges=edges, obstacles=[])
    detour = run_route(
        nodes=nodes,
        edges=edges,
        obstacles=[record(ext_id=201, from_node_id=2, to_node_id=6)],
    )

    assert direct["distance_m"] == pytest.approx(2.0)
    assert [edge["ext_id"] for edge in direct["path_edges"]] == [101]
    assert detour["distance_m"] == pytest.approx(6.0)
    assert [edge["ext_id"] for edge in detour["path_edges"]] == [102, 103, 104]


def test_cross_floor_edges_are_routable_and_ignore_planar_obstacles():
    nodes = [
        record(id=1, ext_id=1, floor_level=1, x_m=0, y_m=0),
        record(id=2, ext_id=2, floor_level=1, x_m=1, y_m=-1),
        record(id=3, ext_id=3, floor_level=2, x_m=3, y_m=4),
        record(id=4, ext_id=4, floor_level=1, x_m=1, y_m=1),
    ]
    edges = [record(ext_id=101, from_node_id=1, to_node_id=3, weight_multiplier=1)]
    obstacles = [record(ext_id=201, from_node_id=2, to_node_id=4)]

    result = run_route(nodes=nodes, edges=edges, obstacles=obstacles)

    assert result["distance_m"] == pytest.approx(5.0)
    assert [edge["ext_id"] for edge in result["path_edges"]] == [101]
