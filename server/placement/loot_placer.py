"""
Loot Placer — розміщує предмети в кімнатах.

Правила:
- entrance:  нічого або стартовий предмет
- treasure:  багато луту (gold, sword, potion)
- combat:    невеликий лут після ворогів
- generic:   рідкісний лут
- boss:      найкращий лут
"""

from __future__ import annotations
import random
from protocol import LootItem, Room

# ─── Таблиці луту ─────────────────────────────────────────────────────────────

ROOM_LOOT_TABLE: dict[str, list[dict]] = {
    "entrance": [
        {"kind": "potion", "value": 1, "count": (0, 1)},
    ],
    "treasure": [
        {"kind": "gold",   "value": 10, "count": (2, 4)},
        {"kind": "sword",  "value": 5,  "count": (0, 1)},
        {"kind": "potion", "value": 2,  "count": (1, 2)},
    ],
    "combat": [
        {"kind": "gold",   "value": 3, "count": (0, 2)},
        {"kind": "potion", "value": 1, "count": (0, 1)},
    ],
    "generic": [
        {"kind": "gold",   "value": 1, "count": (0, 1)},
    ],
    "boss": [
        {"kind": "gold",   "value": 20, "count": (1, 1)},
        {"kind": "sword",  "value": 10, "count": (1, 1)},
        {"kind": "key",    "value": 1,  "count": (1, 1)},
    ],
}


# ─── Утиліти ──────────────────────────────────────────────────────────────────

def _free_positions(room: Room, occupied: set[tuple[int, int]]) -> list[tuple[int, int]]:
    positions = []
    for y in range(room.y + 1, room.y + room.h - 1):
        for x in range(room.x + 1, room.x + room.w - 1):
            if (x, y) not in occupied:
                positions.append((x, y))
    return positions


# ─── Публічний інтерфейс ──────────────────────────────────────────────────────

def place_loot(
    rooms: list[Room],
    occupied: set[tuple[int, int]],
    rng: random.Random,
) -> list[LootItem]:
    """
    Розміщує лут в кімнатах.
    occupied — позиції вже зайняті NPC.
    Повертає список LootItem з координатами.
    """
    loot: list[LootItem] = []
    loot_id = 0

    for room in rooms:
        loot_table = ROOM_LOOT_TABLE.get(room.type, ROOM_LOOT_TABLE["generic"])
        if not loot_table:
            continue

        free = _free_positions(room, occupied)
        if not free:
            continue

        rng.shuffle(free)
        pos_idx = 0

        for entry in loot_table:
            min_count, max_count = entry["count"]
            count = rng.randint(min_count, max_count)

            for _ in range(count):
                if pos_idx >= len(free):
                    break

                x, y = free[pos_idx]
                pos_idx += 1
                occupied.add((x, y))

                item = LootItem(
                    id      = loot_id,
                    room_id = room.id,
                    x       = x,
                    y       = y,
                    kind    = entry["kind"],
                    value   = entry["value"],
                )
                loot.append(item)
                loot_id += 1

    return loot