"""
NPC Placer — розміщує ворогів і персонажів в кімнатах.

Правила:
- entrance: тільки merchant (опціонально)
- combat:   1-3 вороги (skeleton, goblin)
- treasure: немає ворогів
- generic:  0-2 вороги випадково
- boss:     1 boss + 1-2 охоронці
"""

from __future__ import annotations
import random
from protocol import NPC, Room

# ─── Таблиці spawn ────────────────────────────────────────────────────────────

COMBAT_NPCS  = ["skeleton", "goblin", "skeleton", "goblin", "zombie"]
GUARD_NPCS   = ["skeleton", "goblin"]

ROOM_NPC_TABLE: dict[str, list[dict]] = {
    "entrance": [],   # порожньо — гравець стартує тут
    "treasure": [],   # охороняти буде AC-3
    "combat": [
        {"kind": "skeleton", "hp": 10, "count": (1, 3)},
        {"kind": "goblin",   "hp": 8,  "count": (1, 2)},
    ],
    "generic": [
        {"kind": "skeleton", "hp": 10, "count": (0, 2)},
    ],
    "boss": [
        {"kind": "boss",    "hp": 50, "count": (1, 1)},
        {"kind": "goblin",  "hp": 8,  "count": (1, 2)},
    ],
}


# ─── Утиліти ──────────────────────────────────────────────────────────────────

def _free_positions(room: Room, occupied: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """Повертає список вільних внутрішніх позицій кімнати (без стін)."""
    positions = []
    for y in range(room.y + 1, room.y + room.h - 1):
        for x in range(room.x + 1, room.x + room.w - 1):
            if (x, y) not in occupied:
                positions.append((x, y))
    return positions


# ─── Публічний інтерфейс ──────────────────────────────────────────────────────

def place_npcs(rooms: list[Room], rng: random.Random) -> list[NPC]:
    """
    Розміщує NPC в кімнатах згідно з таблицею spawn.
    Повертає список NPC з координатами.
    """
    npcs: list[NPC] = []
    occupied: set[tuple[int, int]] = set()
    npc_id = 0

    for room in rooms:
        spawn_table = ROOM_NPC_TABLE.get(room.type, ROOM_NPC_TABLE["generic"])
        if not spawn_table:
            continue

        free = _free_positions(room, occupied)
        if not free:
            continue

        rng.shuffle(free)
        pos_idx = 0

        for entry in spawn_table:
            min_count, max_count = entry["count"]
            count = rng.randint(min_count, max_count)

            for _ in range(count):
                if pos_idx >= len(free):
                    break

                x, y = free[pos_idx]
                pos_idx += 1
                occupied.add((x, y))

                npc = NPC(
                    id      = npc_id,
                    room_id = room.id,
                    x       = x,
                    y       = y,
                    kind    = entry["kind"],
                    hp      = entry["hp"],
                )
                npcs.append(npc)
                npc_id += 1

    return npcs