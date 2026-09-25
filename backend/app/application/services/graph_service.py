from __future__ import annotations

import heapq
import json
import math
from collections.abc import AsyncIterator, Callable
from typing import Any

from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


class WarehouseNotFound(Exception):
    """Raised when a warehouse ID does not exist."""


class ShelfNotFound(Exception):
    """Raised when a shelf external ID does not exist in a warehouse."""


class PathNotFound(Exception):
    """Raised when no traversable route exists between two shelves."""


class GraphService:
    """
    Calculate warehouse routes and shelf-to-shelf distances.

    The service builds an undirected adjacency list, excludes same-floor edges
    intersected by obstacle segments, and uses Dijkstra's algorithm. Cross-floor
    edges remain available because obstacles represent two-dimensional floor geometry.
    """

    def __init__(self, uow_factory: Callable[[], SQLAlchemyUnitOfWork]):
        self._uow_factory = uow_factory

    async def find_path_between_shelves(
        self,
        warehouse_id: int,
        from_shelf_ext_id: int,
        to_shelf_ext_id: int,
    ) -> dict:
        async with self._uow_factory() as uow:
            s_from = await uow.shelves.read_shelf_by_ext_id(warehouse_id, from_shelf_ext_id)
            if s_from is None:
                raise ShelfNotFound(f"Shelf ext_id={from_shelf_ext_id} not found")

            s_to = await uow.shelves.read_shelf_by_ext_id(warehouse_id, to_shelf_ext_id)
            if s_to is None:
                raise ShelfNotFound(f"Shelf ext_id={to_shelf_ext_id} not found")

            start_id = int(s_from.node_id)
            goal_id = int(s_to.node_id)

            nodes = await uow.nodes.read_nodes_by_warehouse(warehouse_id)
            edges = await uow.edges.read_edges_by_warehouse(warehouse_id)
            obstacles = await uow.obstacles.read_obstacles_by_warehouse(warehouse_id)

            coords: dict[int, tuple[float, float]] = {
                int(n.id): (float(n.x_m), float(n.y_m)) for n in nodes
            }
            node_ext_by_id: dict[int, int] = {int(n.id): int(n.ext_id) for n in nodes}
            floor_by_id: dict[int, int] = {int(n.id): int(n.floor_level) for n in nodes}

            if start_id not in coords or goal_id not in coords:
                raise PathNotFound("Start/goal node not found in nodes of this warehouse")

            adj = self._build_adjacency(coords, floor_by_id, edges, obstacles)

            dist, prev = self._dijkstra_with_prev_edge(adj, start_id)

            if goal_id not in dist or math.isinf(dist[goal_id]):
                raise PathNotFound("No path between shelves")

            path_edges_models, path_node_ids = self._reconstruct(prev, start_id, goal_id)
            if not path_edges_models:
                raise PathNotFound("No path between shelves")

            path_edges_out: list[dict[str, Any]] = []
            for i, e in enumerate(path_edges_models):
                u = path_node_ids[i]
                v = path_node_ids[i + 1]
                path_edges_out.append(
                    {
                        "ext_id": int(e.ext_id),
                        "from_node_ext_id": node_ext_by_id[u],
                        "to_node_ext_id": node_ext_by_id[v],
                        "weight_multiplier": float(e.weight_multiplier),
                    }
                )

            return {
                "distance_m": float(dist[goal_id]),
                "path_edges": path_edges_out,
            }

    async def stream_all_shelf_distances_jsonl(self, warehouse_id: int) -> AsyncIterator[bytes]:
        """Stream one JSON object per reachable, unique pair of shelves.

        Each line has the shape:
        {
          "shelf_a": "shelving_code:section_code",
          "shelf_b": "shelving_code:section_code",
          "distance_m": 12.345
        }
        """
        async with self._uow_factory() as uow:
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            nodes = await uow.nodes.read_nodes_by_warehouse(warehouse_id)
            edges = await uow.edges.read_edges_by_warehouse(warehouse_id)
            obstacles = await uow.obstacles.read_obstacles_by_warehouse(warehouse_id)

            coords: dict[int, tuple[float, float]] = {
                int(n.id): (float(n.x_m), float(n.y_m)) for n in nodes
            }
            floor_by_id: dict[int, int] = {int(n.id): int(n.floor_level) for n in nodes}

            shelves = await uow.shelves.read_shelves_by_warehouse(warehouse_id)
            shelf_items: list[tuple[str, int]] = []
            for s in shelves:
                label = f"{s.shelving_code}:{s.section_code}"
                shelf_items.append((label, int(s.node_id)))

            adj = self._build_adjacency(coords, floor_by_id, edges, obstacles)

            shelves_by_node: dict[int, list[str]] = {}
            for label, node_id in shelf_items:
                shelves_by_node.setdefault(node_id, []).append(label)

            unique_nodes = sorted(shelves_by_node.keys())

            for i, start_node in enumerate(unique_nodes):
                dist = self._dijkstra(adj, start_node)

                labels_here = shelves_by_node[start_node]
                if len(labels_here) > 1:
                    for a in range(len(labels_here)):
                        for b in range(a + 1, len(labels_here)):
                            yield (
                                json.dumps(
                                    {
                                        "shelf_a": labels_here[a],
                                        "shelf_b": labels_here[b],
                                        "distance_m": 0.0,
                                    },
                                    ensure_ascii=False,
                                )
                                + "\n"
                            ).encode("utf-8")

                for j in range(i + 1, len(unique_nodes)):
                    other_node = unique_nodes[j]
                    d = dist.get(other_node, math.inf)
                    if math.isinf(d):
                        continue

                    for a_label in shelves_by_node[start_node]:
                        for b_label in shelves_by_node[other_node]:
                            yield (
                                json.dumps(
                                    {
                                        "shelf_a": a_label,
                                        "shelf_b": b_label,
                                        "distance_m": float(d),
                                    },
                                    ensure_ascii=False,
                                )
                                + "\n"
                            ).encode("utf-8")

    @staticmethod
    def _build_adjacency(
        coords: dict[int, tuple[float, float]],
        floor_by_id: dict[int, int],
        edges: list[Any],
        obstacles: list[Any],
    ) -> dict[int, list[tuple[int, float, Any]]]:
        """Build an undirected adjacency list with obstacle-aware edge filtering.

        Obstacles are 2D line segments. They block intersecting edges on the same
        floor, except when the edge and obstacle share an endpoint. Cross-floor
        edges and cross-floor obstacles are not part of this planar check.
        """
        obstacle_segments: list[tuple[int, tuple[float, float], tuple[float, float], set[int]]] = []
        for o in obstacles:
            oa = int(o.from_node_id)
            ob = int(o.to_node_id)
            if oa not in coords or ob not in coords:
                continue

            fa = floor_by_id.get(oa)
            fb = floor_by_id.get(ob)
            if fa is None or fb is None:
                continue

            if fa != fb:
                continue

            obstacle_segments.append((fa, coords[oa], coords[ob], {oa, ob}))

        def _segments_intersect(
            p1: tuple[float, float],
            p2: tuple[float, float],
            q1: tuple[float, float],
            q2: tuple[float, float],
        ) -> bool:
            """Return whether two segments intersect, including collinear contact."""
            EPS = 1e-9

            def orient(a, b, c) -> float:
                return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

            def on_segment(a, b, c) -> bool:
                return (
                    min(a[0], b[0]) - EPS <= c[0] <= max(a[0], b[0]) + EPS
                    and min(a[1], b[1]) - EPS <= c[1] <= max(a[1], b[1]) + EPS
                )

            o1 = orient(p1, p2, q1)
            o2 = orient(p1, p2, q2)
            o3 = orient(q1, q2, p1)
            o4 = orient(q1, q2, p2)

            if ((o1 > EPS and o2 < -EPS) or (o1 < -EPS and o2 > EPS)) and (
                (o3 > EPS and o4 < -EPS) or (o3 < -EPS and o4 > EPS)
            ):
                return True

            if abs(o1) <= EPS and on_segment(p1, p2, q1):
                return True
            if abs(o2) <= EPS and on_segment(p1, p2, q2):
                return True
            if abs(o3) <= EPS and on_segment(q1, q2, p1):
                return True
            if abs(o4) <= EPS and on_segment(q1, q2, p2):
                return True

            return False

        adj: dict[int, list[tuple[int, float, Any]]] = {nid: [] for nid in coords.keys()}

        for e in edges:
            a = int(e.from_node_id)
            b = int(e.to_node_id)
            if a not in coords or b not in coords:
                continue

            fa = floor_by_id.get(a)
            fb = floor_by_id.get(b)
            check_obstacles = fa is not None and fb is not None and fa == fb

            if check_obstacles and obstacle_segments:
                p1 = coords[a]
                p2 = coords[b]
                floor = fa

                blocked = False
                for obs_floor, q1, q2, endpoints in obstacle_segments:
                    if obs_floor != floor:
                        continue

                    if a in endpoints or b in endpoints:
                        continue

                    if _segments_intersect(p1, p2, q1, q2):
                        blocked = True
                        break

                if blocked:
                    continue

            ax, ay = coords[a]
            bx, by = coords[b]
            base = math.hypot(ax - bx, ay - by)
            w = base * float(e.weight_multiplier)

            adj[a].append((b, w, e))
            adj[b].append((a, w, e))

        return adj

    @staticmethod
    def _dijkstra(adj: dict[int, list[tuple[int, float, Any]]], start: int) -> dict[int, float]:
        """Return distances from the start node to every reachable node."""
        dist: dict[int, float] = {start: 0.0}
        pq: list[tuple[float, int]] = [(0.0, start)]

        while pq:
            d, u = heapq.heappop(pq)
            if d != dist.get(u, math.inf):
                continue

            for v, w, _edge_model in adj.get(u, []):
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    heapq.heappush(pq, (nd, v))

        return dist

    @staticmethod
    def _dijkstra_with_prev_edge(
        adj: dict[int, list[tuple[int, float, Any]]],
        start: int,
    ) -> tuple[dict[int, float], dict[int, tuple[int, Any] | None]]:
        """Return distances and predecessor edges for path reconstruction."""
        dist: dict[int, float] = {start: 0.0}
        prev: dict[int, tuple[int, Any] | None] = {start: None}
        pq: list[tuple[float, int]] = [(0.0, start)]

        while pq:
            d, u = heapq.heappop(pq)
            if d != dist.get(u, math.inf):
                continue

            for v, w, edge_model in adj.get(u, []):
                nd = d + w
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    prev[v] = (u, edge_model)
                    heapq.heappush(pq, (nd, v))

        return dist, prev

    @staticmethod
    def _reconstruct(
        prev: dict[int, tuple[int, Any] | None],
        start: int,
        goal: int,
    ) -> tuple[list[Any], list[int]]:
        """Reconstruct ordered edge models and node IDs from predecessors."""
        cur = goal
        edges_rev: list[Any] = []
        nodes_rev: list[int] = [cur]

        while cur != start:
            p = prev.get(cur)
            if p is None:
                return [], []
            parent, edge_model = p
            edges_rev.append(edge_model)
            cur = parent
            nodes_rev.append(cur)

        nodes = list(reversed(nodes_rev))
        edges = list(reversed(edges_rev))
        return edges, nodes
