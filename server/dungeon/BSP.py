"""
BSP (Binary Space Partitioning) генератор кімнат.

Алгоритм:
1. Починаємо з одного прямокутника (весь простір)
2. Рекурсивно ділимо його на два — горизонтально або вертикально
3. В кожному листі дерева створюємо кімнату (трохи менше за вузол)
4. Повертаємо список Room з координатами
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field

from protocol import Room

# ─── Константи ────────────────────────────────────────────────────────────────

MIN_NODE_SIZE = 6    # мінімальний розмір вузла BSP (в тайлах)
MIN_ROOM_SIZE = 3    # мінімальний розмір кімнати всередині вузла
ROOM_PADDING  = 1    # відступ кімнати від краю вузла


# ─── BSP вузол ────────────────────────────────────────────────────────────────

@dataclass
class BSPNode:
    x: int
    y: int
    w: int
    h: int
    left:  BSPNode | None = field(default=None, repr=False)
    right: BSPNode | None = field(default=None, repr=False)
    room:  Room    | None = field(default=None, repr=False)

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def center(self) -> tuple[int, int]:
        if self.room:
            cx = self.room.x + self.room.w // 2
            cy = self.room.y + self.room.h // 2
            return cx, cy
        return self.x + self.w // 2, self.y + self.h // 2


# ─── Розбивка дерева ──────────────────────────────────────────────────────────

def _split(node: BSPNode, rng: random.Random, depth: int) -> None:
    """Рекурсивно ділить вузол на два дочірніх."""
    if depth <= 0:
        return

    can_split_h = node.h >= MIN_NODE_SIZE * 2
    can_split_v = node.w >= MIN_NODE_SIZE * 2

    if not can_split_h and not can_split_v:
        return

    # Якщо можна ділити в обидва боки — обираємо випадково,
    # але з bias до більшого виміру щоб кімнати були рівномірніші
    if can_split_h and can_split_v:
        split_horizontal = rng.random() < (node.h / (node.w + node.h))
    else:
        split_horizontal = can_split_h

    if split_horizontal:
        cut = rng.randint(MIN_NODE_SIZE, node.h - MIN_NODE_SIZE)
        node.left  = BSPNode(node.x, node.y,       node.w, cut)
        node.right = BSPNode(node.x, node.y + cut, node.w, node.h - cut)
    else:
        cut = rng.randint(MIN_NODE_SIZE, node.w - MIN_NODE_SIZE)
        node.left  = BSPNode(node.x,       node.y, cut,           node.h)
        node.right = BSPNode(node.x + cut, node.y, node.w - cut,  node.h)

    _split(node.left,  rng, depth - 1)
    _split(node.right, rng, depth - 1)


# ─── Створення кімнат ─────────────────────────────────────────────────────────

ROOM_TYPES = ["generic", "generic", "generic", "combat", "combat", "treasure", "entrance"]

def _create_rooms(node: BSPNode, rooms: list[Room], rng: random.Random) -> None:
    """Обходить листя дерева і створює кімнату в кожному."""
    if node.is_leaf:
        max_w = node.w - ROOM_PADDING * 2
        max_h = node.h - ROOM_PADDING * 2

        if max_w < MIN_ROOM_SIZE or max_h < MIN_ROOM_SIZE:
            return

        rw = rng.randint(MIN_ROOM_SIZE, max_w)
        rh = rng.randint(MIN_ROOM_SIZE, max_h)
        rx = node.x + ROOM_PADDING + rng.randint(0, max_w - rw)
        ry = node.y + ROOM_PADDING + rng.randint(0, max_h - rh)

        room = Room(
            id     = len(rooms),
            x      = rx,
            y      = ry,
            w      = rw,
            h      = rh,
            type   = rng.choice(ROOM_TYPES),
            center = (rx + rw // 2, ry + rh // 2),
        )
        node.room = room
        rooms.append(room)
        return

    if node.left:
        _create_rooms(node.left,  rooms, rng)
    if node.right:
        _create_rooms(node.right, rooms, rng)


# ─── Збір пар для коридорів ───────────────────────────────────────────────────

def _collect_pairs(node: BSPNode, pairs: list[tuple[BSPNode, BSPNode]]) -> BSPNode | None:
    """
    Піднімається по дереву і збирає пари (лівий листок, правий листок)
    щоб потім з'єднати їх коридором.
    """
    if node.is_leaf:
        return node

    left_leaf  = _collect_pairs(node.left,  pairs) if node.left  else None
    right_leaf = _collect_pairs(node.right, pairs) if node.right else None

    if left_leaf and right_leaf:
        pairs.append((left_leaf, right_leaf))
        # Повертаємо будь-який з листків вгору для наступного рівня
        return left_leaf if left_leaf.room else right_leaf

    return left_leaf or right_leaf


# ─── Публічний інтерфейс ──────────────────────────────────────────────────────

@dataclass
class BSPResult:
    rooms: list[Room]
    pairs: list[tuple[BSPNode, BSPNode]]   # пари вузлів для A*
    root:  BSPNode


def generate_bsp(size: int, seed: int) -> BSPResult:
    """
    Головна функція. Повертає BSPResult з кімнатами і парами для коридорів.

    Args:
        size: розмір карти (size x size тайлів)
        seed: seed для відтворюваності
    """
    rng   = random.Random(seed)
    root  = BSPNode(0, 0, size, size)
    depth = max(3, size // 8)   # глибина залежить від розміру карти

    _split(root, rng, depth)

    rooms: list[Room] = []
    _create_rooms(root, rooms, rng)

    # Перша кімната завжди entrance
    if rooms:
        rooms[0].type = "entrance"

    pairs: list[tuple[BSPNode, BSPNode]] = []
    _collect_pairs(root, pairs)

    return BSPResult(rooms=rooms, pairs=pairs, root=root)