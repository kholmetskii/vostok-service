from __future__ import annotations

import json
import math
import heapq
from collections.abc import AsyncIterator, Callable
from typing import Any


from app.infrastructure.db.uow import SQLAlchemyUnitOfWork


class WarehouseNotFound(Exception):
    """Warehouse с указанным id не найден."""
    pass


class ShelfNotFound(Exception):
    """Shelf с указанным ext_id не найдена (в рамках warehouse)."""
    pass


class PathNotFound(Exception):
    """Путь между полками не найден (граф разорван / ребра заблокированы obstacles)."""
    pass


class GraphService:
    """
    Application service: вся логика графа склада.

    Сценарии:
    1) find_path_between_shelves:
       - строим граф для склада (nodes+edges, с фильтрацией по obstacles)
       - запускаем Dijkstra
       - возвращаем distance_m + path_edges (List[EdgeOut])

    2) stream_all_shelf_distances_jsonl:
       - строим граф один раз
       - для каждого стартового node_id полок запускаем Dijkstra
       - отдаём JSONL: {"shelf_a": "...", "shelf_b": "...", "distance_m": ...}\n
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
            # 1) shelves -> node_id
            s_from = await uow.shelves.read_shelf_by_ext_id(warehouse_id, from_shelf_ext_id)
            if s_from is None:
                raise ShelfNotFound(f"Shelf ext_id={from_shelf_ext_id} not found")

            s_to = await uow.shelves.read_shelf_by_ext_id(warehouse_id, to_shelf_ext_id)
            if s_to is None:
                raise ShelfNotFound(f"Shelf ext_id={to_shelf_ext_id} not found")

            start_id = int(s_from.node_id)
            goal_id = int(s_to.node_id)

            # 2) load nodes + edges + obstacles
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

            # 3) build adjacency (с исключением рёбер, пересечённых obstacles)
            # adjacency: node_id -> [(neighbor_id, weight, edge_model)]
            adj = self._build_adjacency(coords, floor_by_id, edges, obstacles)

            # 4) Dijkstra, prev хранит (parent_node_id, edge_model)
            dist, prev = self._dijkstra_with_prev_edge(adj, start_id)

            if goal_id not in dist or math.isinf(dist[goal_id]):
                raise PathNotFound("No path between shelves")

            # 5) восстановление списка edge_model + node_ids пути
            path_edges_models, path_node_ids = self._reconstruct(prev, start_id, goal_id)
            if not path_edges_models:
                raise PathNotFound("No path between shelves")

            # 6) собрать EdgeOut-совместимый список
            # EdgeOut: ext_id, from_node_ext_id, to_node_ext_id, weight_multiplier
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
        """
        Отдаёт JSONL поток (по строке на пару полок):
        {
          "shelf_a": "shelving_code:section_code",
          "shelf_b": "shelving_code:section_code",
          "distance_m": 12.345
        }
        """
        async with self._uow_factory() as uow:
            # Проверяем, что склад существует (иначе 404 наверху в роутере)
            warehouse = await uow.warehouses.read_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFound(f"Warehouse {warehouse_id} not found")

            # Данные графа
            nodes = await uow.nodes.read_nodes_by_warehouse(warehouse_id)
            edges = await uow.edges.read_edges_by_warehouse(warehouse_id)
            obstacles = await uow.obstacles.read_obstacles_by_warehouse(warehouse_id)

            coords: dict[int, tuple[float, float]] = {
                int(n.id): (float(n.x_m), float(n.y_m)) for n in nodes
            }
            floor_by_id: dict[int, int] = {int(n.id): int(n.floor_level) for n in nodes}

            # Полки: label + node_id
            shelves = await uow.shelves.read_shelves_by_warehouse(warehouse_id)
            shelf_items: list[tuple[str, int]] = []
            for s in shelves:
                label = f"{s.shelving_code}:{s.section_code}"
                shelf_items.append((label, int(s.node_id)))

            # Строим граф один раз
            adj = self._build_adjacency(coords, floor_by_id, edges, obstacles)

            # Группируем полки по node_id (если несколько полок привязаны к одной ноде)
            shelves_by_node: dict[int, list[str]] = {}
            for label, node_id in shelf_items:
                shelves_by_node.setdefault(node_id, []).append(label)

            unique_nodes = sorted(shelves_by_node.keys())

            # Для каждого стартового узла полок считаем дистанции до всех (Dijkstra)
            for i, start_node in enumerate(unique_nodes):
                dist = self._dijkstra(adj, start_node)

                # 1) пары полок внутри одного node_id => distance = 0
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

                # 2) пары с другими node_id (j > i), чтобы не было дубликатов
                for j in range(i + 1, len(unique_nodes)):
                    other_node = unique_nodes[j]
                    d = dist.get(other_node, math.inf)
                    if math.isinf(d):
                        # пути нет — можно пропускать (или отдавать distance_m=null)
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

    # ----------------- internal helpers -----------------

    @staticmethod
    def _build_adjacency(
        coords: dict[int, tuple[float, float]],
        floor_by_id: dict[int, int],
        edges: list[Any],
        obstacles: list[Any],
    ) -> dict[int, list[tuple[int, float, Any]]]:
        """
        Строим adjacency список:
        node_id -> [(neighbor_id, weight, edge_model)]

        Фильтрация по obstacles:
        - obstacles считаем как "стены" (отрезки) в 2D
        - ребро исключаем, если отрезок ребра пересекает отрезок obstacle
        - пересечения считаем только для ребер на ОДНОМ этаже
          (лестницы/межэтажные edges не фильтруем obstacles)
        - если edge и obstacle имеют общий endpoint, это НЕ блокировка (разрешаем касание в узле)
        """
        # --- precompute obstacle segments (only meaningful in 2D on a single floor) ---
        # obstacle_segments: (floor_level, p1, p2, endpoints_set[node_id])
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

            # препятствие между этажами для 2D-пересечений не имеет смысла — игнорируем
            if fa != fb:
                continue

            obstacle_segments.append((fa, coords[oa], coords[ob], {oa, ob}))

        def _segments_intersect(
            p1: tuple[float, float],
            p2: tuple[float, float],
            q1: tuple[float, float],
            q2: tuple[float, float],
        ) -> bool:
            """
            True если отрезки p1-p2 и q1-q2 пересекаются (включая касания/коллинеарность).
            Достаточно для блокировки рёбер препятствиями.
            """
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

            # общий случай
            if ((o1 > EPS and o2 < -EPS) or (o1 < -EPS and o2 > EPS)) and (
                (o3 > EPS and o4 < -EPS) or (o3 < -EPS and o4 > EPS)
            ):
                return True

            # граничные случаи
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

            # --- если edge на одном этаже, проверяем пересечения с obstacles на том же этаже ---
            fa = floor_by_id.get(a)
            fb = floor_by_id.get(b)
            check_obstacles = (fa is not None and fb is not None and fa == fb)

            if check_obstacles and obstacle_segments:
                p1 = coords[a]
                p2 = coords[b]
                floor = fa

                blocked = False
                for obs_floor, q1, q2, endpoints in obstacle_segments:
                    if obs_floor != floor:
                        continue

                    # если edge и obstacle делят общий endpoint — считаем допустимым
                    if a in endpoints or b in endpoints:
                        continue

                    if _segments_intersect(p1, p2, q1, q2):
                        blocked = True
                        break

                # если пересеклось препятствием — исключаем ребро из графа
                if blocked:
                    continue

            ax, ay = coords[a]
            bx, by = coords[b]
            base = math.hypot(ax - bx, ay - by)
            w = base * float(e.weight_multiplier)

            # неориентированный граф: добавляем оба направления
            adj[a].append((b, w, e))
            adj[b].append((a, w, e))

        return adj

    @staticmethod
    def _dijkstra(adj: dict[int, list[tuple[int, float, Any]]], start: int) -> dict[int, float]:
        """
        Обычный Dijkstra: возвращает dist до всех достижимых нод.
        edge_model нам здесь не нужен — но он лежит в adjacency.
        """
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
        """
        Dijkstra для восстановления пути:
        - dist[node] = расстояние
        - prev[node] = (parent_node_id, edge_model) или None для start
        """
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
        """
        Восстанавливает путь:
        - edges_models: [e1, e2, ...] в порядке пути
        - node_ids: [n0, n1, ..., nk]
        """
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