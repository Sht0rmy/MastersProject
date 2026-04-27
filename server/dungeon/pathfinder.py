"""
A* пошук шляху для коридорів між кімнатами.
Коридори уникають проходження впритул до стін кімнат.
"""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from protocol import Room, Corridor

Point = tuple[int, int]


@dataclass(order=True)
class _Node:
    f: float
    g: float = field(compare=False)
    pos: Point = field(compare=False)
    parent: "_Node | None" = field(default=None, compare=False)


def _heuristic(a: Point, b: Point) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: Point, grid_w: int, grid_h: int) -> list[Point]:
    x, y = pos
    result = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_w and 0 <= ny < grid_h:
            result.append((nx, ny))
    return result


def _build_cost_map(
    rooms: list[Room],
    grid_w: int,
    grid_h: int,
) -> dict[Point, float]:
    """
    Будує карту вартості проходу.
    - Підлога кімнати: непрохідна (999) — коридори не йдуть через кімнати
    - Стіна кімнати: дуже дорого (50) — коридори уникають стін
    - Сусід стіни кімнати (відступ 1): дорого (10) — коридори не йдуть впритул
    - Відкритий простір: дешево (1)
    """
    cost: dict[Point, float] = {}
    wall_cells: set[Point] = set()
    floor_cells: set[Point] = set()

    for room in rooms:
        for ty in range(room.y, room.y + room.h):
            for tx in range(room.x, room.x + room.w):
                is_wall = (tx == room.x or tx == room.x + room.w - 1 or
                           ty == room.y or ty == room.y + room.h - 1)
                if is_wall:
                    wall_cells.add((tx, ty))
                    cost[(tx, ty)] = 50.0
                else:
                    floor_cells.add((tx, ty))
                    cost[(tx, ty)] = 999.0  # не проходимо через підлогу кімнати

    # Додаємо вартість для клітинок впритул до стін (відступ 1 тайл)
    for wx, wy in wall_cells:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nb = (wx + dx, wy + dy)
                if nb not in wall_cells and nb not in floor_cells:
                    if cost.get(nb, 1.0) < 10.0:
                        cost[nb] = 10.0

    return cost


def astar(
    start: Point,
    end: Point,
    cost_map: dict[Point, float],
    grid_w: int,
    grid_h: int,
) -> list[Point]:
    if start == end:
        return [start]

    open_heap: list[_Node] = []
    open_set: dict[Point, _Node] = {}
    closed: set[Point] = set()

    start_node = _Node(f=_heuristic(start, end), g=0, pos=start)
    heapq.heappush(open_heap, start_node)
    open_set[start] = start_node

    while open_heap:
        current = heapq.heappop(open_heap)

        if current.pos in closed:
            continue
        closed.add(current.pos)

        if current.pos == end:
            path = []
            node: _Node | None = current
            while node:
                path.append(node.pos)
                node = node.parent
            path.reverse()
            return path

        for nb in _neighbors(current.pos, grid_w, grid_h):
            if nb in closed:
                continue

            cell_cost = cost_map.get(nb, 1.0)
            # Підлогу кімнат дозволяємо тільки для start/end точок
            if cell_cost >= 999.0 and nb != end and nb != start:
                continue

            g = current.g + cell_cost
            f = g + _heuristic(nb, end)

            if nb in open_set and open_set[nb].g <= g:
                continue

            node = _Node(f=f, g=g, pos=nb, parent=current)
            heapq.heappush(open_heap, node)
            open_set[nb] = node

    return _l_shaped(start, end)


def _l_shaped(start: Point, end: Point) -> list[Point]:
    path = []
    x, y = start
    ex, ey = end
    while x != ex:
        path.append((x, y))
        x += 1 if ex > x else -1
    while y != ey:
        path.append((x, y))
        y += 1 if ey > y else -1
    path.append(end)
    return path


def build_corridors(
    pairs: list[tuple],
    grid_w: int,
    grid_h: int,
    rooms: list[Room] | None = None,
) -> list[dict]:
    cost_map = _build_cost_map(rooms or [], grid_w, grid_h)
    corridors: list[dict] = []

    for left, right in pairs:
        if not left.room or not right.room:
            continue

        # Стартуємо з підлоги лівої кімнати, найближчої до правої
        # Закінчуємо підлогою правої кімнати, найближчої до лівої
        start = _closest_floor_to(right.room.center, left.room)
        end   = _closest_floor_to(left.room.center, right.room)

        path = astar(start, end, cost_map, grid_w, grid_h)

        corridor = Corridor(
            from_room=left.room.id,
            to_room=right.room.id,
            path=[list(p) for p in path],
        )
        corridors.append(corridor.to_dict())

    return corridors


def _room_floor_cells(room: Room) -> list[Point]:
    """Повертає всі внутрішні тайли кімнати (без стін)."""
    cells = []
    for ty in range(room.y + 1, room.y + room.h - 1):
        for tx in range(room.x + 1, room.x + room.w - 1):
            cells.append((tx, ty))
    return cells


def _closest_floor_to(point: Point, room: Room) -> Point:
    """Знаходить найближчий внутрішній тайл кімнати до зовнішньої точки."""
    best = room.center
    best_dist = float("inf")
    for cell in _room_floor_cells(room):
        d = abs(cell[0] - point[0]) + abs(cell[1] - point[1])
        if d < best_dist:
            best_dist = d
            best = cell
    return best