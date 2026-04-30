"""
GreedyPlacer — жадібний алгоритм.
Розміщує NPC/лут за простими правилами БЕЗ CSP/AC-3.
Перевіряє правила після розміщення (post-hoc), не до.
"""

from __future__ import annotations
import random
from protocol import NPC, LootItem, Room

ROOM_NPC_TABLE = {
    "entrance": [],
    "treasure": [],
    "merchant": [{"kind": "merchant", "hp": 999, "count": (1, 1)}],
    "combat":   [{"kind": "skeleton", "hp": 10, "count": (1, 3)},
                 {"kind": "goblin",   "hp": 8,  "count": (0, 2)}],
    "generic":  [{"kind": "skeleton", "hp": 10, "count": (0, 2)}],
    "boss":     [{"kind": "boss",     "hp": 50, "count": (1, 1)},
                 {"kind": "goblin",   "hp": 8,  "count": (0, 2)}],
}

ROOM_LOOT_TABLE = {
    "entrance": [{"kind": "potion", "value": 1, "count": (0, 1)}],
    "treasure": [{"kind": "gold",   "value": 10, "count": (2, 4)},
                 {"kind": "sword",  "value": 5,  "count": (0, 1)}],
    "combat":   [{"kind": "gold",   "value": 3,  "count": (0, 2)}],
    "generic":  [{"kind": "gold",   "value": 1,  "count": (0, 1)}],
    # Жадібний алгоритм НЕ перевіряє — може поставити лут в merchant/boss
    "merchant": [{"kind": "gold",   "value": 5,  "count": (0, 2)}],
    "boss":     [{"kind": "sword",  "value": 10, "count": (0, 1)},
                 {"kind": "gold",   "value": 5,  "count": (0, 2)}],
}


def _free_positions(room: Room, occupied: set[tuple[int, int]]) -> list[tuple[int, int]]:
    positions = []
    for y in range(room.y + 1, room.y + room.h - 1):
        for x in range(room.x + 1, room.x + room.w - 1):
            if (x, y) not in occupied:
                positions.append((x, y))
    return positions


def greedy_place_npcs(rooms: list[Room], rng: random.Random) -> list[NPC]:
    """Жадібне розміщення — використовує таблицю але без constraint перевірки."""
    npcs: list[NPC] = []
    occupied: set[tuple[int, int]] = set()
    npc_id = 0

    for room in rooms:
        table = ROOM_NPC_TABLE.get(room.type, ROOM_NPC_TABLE["generic"])
        free = _free_positions(room, occupied)
        if not free:
            continue
        rng.shuffle(free)
        pos_idx = 0

        for entry in table:
            count = rng.randint(*entry["count"])
            for _ in range(count):
                if pos_idx >= len(free):
                    break
                x, y = free[pos_idx]
                pos_idx += 1
                occupied.add((x, y))
                npcs.append(NPC(
                    id=npc_id, room_id=room.id,
                    x=x, y=y,
                    kind=entry["kind"], hp=entry["hp"],
                ))
                npc_id += 1

    return npcs


def greedy_place_loot(
    rooms: list[Room],
    occupied: set[tuple[int, int]],
    rng: random.Random,
) -> list[LootItem]:
    """Жадібне розміщення луту — без перевірки merchant/boss обмежень."""
    loot: list[LootItem] = []
    loot_id = 0

    for room in rooms:
        table = ROOM_LOOT_TABLE.get(room.type, ROOM_LOOT_TABLE["generic"])
        free = _free_positions(room, occupied)
        if not free:
            continue
        rng.shuffle(free)
        pos_idx = 0

        for entry in table:
            count = rng.randint(*entry["count"])
            for _ in range(count):
                if pos_idx >= len(free):
                    break
                x, y = free[pos_idx]
                pos_idx += 1
                occupied.add((x, y))
                loot.append(LootItem(
                    id=loot_id, room_id=room.id,
                    x=x, y=y,
                    kind=entry["kind"], value=entry["value"],
                ))
                loot_id += 1

    return loot