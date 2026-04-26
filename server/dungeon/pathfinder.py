"""
A* пошук шляху для коридорів між кімнатами.

Алгоритм:
1. Отримує дві точки (центри кімнат)
2. Будує сітку прохідності (де є стіни/кімнати)
3. Знаходить найкоротший шлях між точками
4. Повертає список тайлів [[x,y], ...] для коридору
"""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field


# ─── Типи ─────────────────────────────────────────────────────────────────────

Point = tuple[int, int]


# ─── A* ───────────────────────────────────────────────────────────────────────

@dataclass(order=True)
class _Node:
    f: float
    g: float         = field(compare=False)
    pos: Point       = field(compare=False)
    parent: "_Node | None" = field(default=None, compare=False)


def _heuristic(a: Point, b: Point) -> float:
    """Manhattan відстань."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(pos: Point, grid_w: int, grid_h: int) -> list[Point]:
    """4-напрямкові сусіди (без діагоналей — коридори прямі)."""
    x, y = pos
    result = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_w and 0 <= ny < grid_h:
            result.append((nx, ny))
    return result


def astar(
    start: Point,
    end: Point,
    blocked: set[Point],
    grid_w: int,
    grid_h: int,
) -> list[Point]:
    """
    Знаходить шлях від start до end уникаючи blocked клітинок.
    Повертає список точок включно зі start і end.
    Якщо шлях не знайдено — повертає пряму лінію (fallback).
    """
    if start == end:
        return [start]

    open_heap: list[_Node] = []
    open_set:  dict[Point, _Node] = {}
    closed:    set[Point] = set()

    start_node = _Node(f=_heuristic(start, end), g=0, pos=start)
    heapq.heappush(open_heap, start_node)
    open_set[start] = start_node

    while open_heap:
        current = heapq.heappop(open_heap)

        if current.pos in closed:
            continue
        closed.add(current.pos)

        if current.pos == end:
            # Відновлюємо шлях
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

            # Коридори можуть проходити крізь стіни, але стіни дорожчі
            cost = 1.0 if nb not in blocked else 5.0
            g = current.g + cost
            f = g + _heuristic(nb, end)

            if nb in open_set and open_set[nb].g <= g:
                continue

            node = _Node(f=f, g=g, pos=nb, parent=current)
            heapq.heappush(open_heap, node)
            open_set[nb] = node

    # Fallback: пряма L-подібна лінія якщо A* не знайшов шлях
    return _l_shaped(start, end)


def _l_shaped(start: Point, end: Point) -> list[Point]:
    """Простий L-подібний коридор як fallback."""
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


# ─── Публічний інтерфейс ──────────────────────────────────────────────────────

def build_corridors(
    pairs: list[tuple],          # list of (BSPNode, BSPNode)
    grid_w: int,
    grid_h: int,
) -> list[dict]:
    """
    Для кожної пари вузлів будує коридор між центрами їх кімнат.
    Повертає список dict сумісних з Corridor.to_dict().
    """
    from protocol import Corridor

    corridors: list[dict] = []

    # Збираємо всі тайли кімнат як "дорогі" для проходу
    # (коридори краще йдуть по відкритому простору)
    blocked: set[Point] = set()

    for left, right in pairs:
        if not left.room or not right.room:
            continue

        start = left.room.center
        end   = right.room.center

        path = astar(start, end, blocked, grid_w, grid_h)

        corridor = Corridor(
            from_room = left.room.id,
            to_room   = right.room.id,
            path      = [list(p) for p in path],
        )
        corridors.append(corridor.to_dict())

    return corridors