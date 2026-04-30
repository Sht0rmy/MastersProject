"""
BSP генератор кімнат з обмеженням пропорцій.
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field

from protocol import Room

MIN_NODE_SIZE  = 5 #instead of 7
MIN_ROOM_SIZE  = 3 #instead of 4
ROOM_PADDING   = 1

# Максимальне співвідношення сторін кімнати (w/h або h/w)
# 1.8 означає кімната не може бути вужчою ніж 1:1.8
MAX_ASPECT_RATIO = 1.8


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
            return self.room.x + self.room.w // 2, self.room.y + self.room.h // 2
        return self.x + self.w // 2, self.y + self.h // 2


def _split(node: BSPNode, rng: random.Random, depth: int) -> None:
    if depth <= 0:
        return

    can_split_h = node.h >= MIN_NODE_SIZE * 2
    can_split_v = node.w >= MIN_NODE_SIZE * 2

    if not can_split_h and not can_split_v:
        return

    # Bias до розбивки більшого виміру — уникаємо витягнутих вузлів
    if can_split_h and can_split_v:
        # Якщо вузол сильно витягнутий — ділимо по більшому виміру
        if node.w / node.h > 1.5:
            split_horizontal = False
        elif node.h / node.w > 1.5:
            split_horizontal = True
        else:
            split_horizontal = rng.random() < 0.5
    else:
        split_horizontal = can_split_h

    if split_horizontal:
        cut = rng.randint(MIN_NODE_SIZE, node.h - MIN_NODE_SIZE)
        node.left  = BSPNode(node.x, node.y,       node.w, cut)
        node.right = BSPNode(node.x, node.y + cut, node.w, node.h - cut)
    else:
        cut = rng.randint(MIN_NODE_SIZE, node.w - MIN_NODE_SIZE)
        node.left  = BSPNode(node.x,       node.y, cut,          node.h)
        node.right = BSPNode(node.x + cut, node.y, node.w - cut, node.h)

    _split(node.left,  rng, depth - 1)
    _split(node.right, rng, depth - 1)


ROOM_TYPES = ["generic", "generic", "generic", "combat", "combat", "treasure", "entrance"]


def _create_rooms(node: BSPNode, rooms: list[Room], rng: random.Random) -> None:
    if node.is_leaf:
        max_w = node.w - ROOM_PADDING * 2
        max_h = node.h - ROOM_PADDING * 2

        if max_w < MIN_ROOM_SIZE or max_h < MIN_ROOM_SIZE:
            return

        # Генеруємо розміри з обмеженням на пропорції
        for _ in range(10):  # 10 спроб знайти гарні пропорції
            rw = rng.randint(MIN_ROOM_SIZE, max_w)
            rh = rng.randint(MIN_ROOM_SIZE, max_h)

            aspect = max(rw, rh) / max(min(rw, rh), 1)
            if aspect <= MAX_ASPECT_RATIO:
                break
            # Якщо занадто витягнута — підтягуємо меншу сторону
            if rw > rh:
                rh = max(MIN_ROOM_SIZE, int(rw / MAX_ASPECT_RATIO))
            else:
                rw = max(MIN_ROOM_SIZE, int(rh / MAX_ASPECT_RATIO))

        # Обмежуємо щоб не виходило за межі вузла
        rw = min(rw, max_w)
        rh = min(rh, max_h)

        rx = node.x + ROOM_PADDING + rng.randint(0, max(0, max_w - rw))
        ry = node.y + ROOM_PADDING + rng.randint(0, max(0, max_h - rh))

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


def _collect_pairs(node: BSPNode, pairs: list[tuple[BSPNode, BSPNode]]) -> BSPNode | None:
    if node.is_leaf:
        return node

    left_leaf  = _collect_pairs(node.left,  pairs) if node.left  else None
    right_leaf = _collect_pairs(node.right, pairs) if node.right else None

    if left_leaf and right_leaf:
        pairs.append((left_leaf, right_leaf))
        return left_leaf if left_leaf.room else right_leaf

    return left_leaf or right_leaf


@dataclass
class BSPResult:
    rooms: list[Room]
    pairs: list[tuple[BSPNode, BSPNode]]
    root:  BSPNode


def generate_bsp(size: int, seed: int) -> BSPResult:
    rng   = random.Random(seed)
    root  = BSPNode(0, 0, size, size)
    depth = max(3, size // 8)

    _split(root, rng, depth)

    rooms: list[Room] = []
    _create_rooms(root, rooms, rng)

    if rooms:
        rooms[0].type = "entrance"

    pairs: list[tuple[BSPNode, BSPNode]] = []
    _collect_pairs(root, pairs)

    return BSPResult(rooms=rooms, pairs=pairs, root=root)