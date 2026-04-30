"""
RandomPlacer — повністю випадкове розміщення NPC і луту.
Використовується як baseline для порівняння з AC-3.
"""

from __future__ import annotations
import random
from protocol import NPC, LootItem, Room

NPC_KINDS  = ["skeleton", "goblin", "boss", "merchant"]
LOOT_KINDS = ["gold", "sword", "potion", "key"]


def _free_positions(room: Room, occupied: set[tuple[int, int]]) -> list[tuple[int, int]]:
    positions = []
    for y in range(room.y + 1, room.y + room.h - 1):
        for x in range(room.x + 1, room.x + room.w - 1):
            if (x, y) not in occupied:
                positions.append((x, y))
    return positions


def random_place_npcs(rooms: list[Room], rng: random.Random) -> list[NPC]:
    """Розміщує NPC повністю випадково — без урахування типу кімнати."""
    npcs: list[NPC] = []
    occupied: set[tuple[int, int]] = set()
    npc_id = 0

    for room in rooms:
        free = _free_positions(room, occupied)
        if not free:
            continue
        rng.shuffle(free)
        # Випадкова кількість NPC (0-3) в будь-якій кімнаті
        count = rng.randint(0, min(3, len(free)))
        for i in range(count):
            x, y = free[i]
            occupied.add((x, y))
            npcs.append(NPC(
                id=npc_id, room_id=room.id,
                x=x, y=y,
                kind=rng.choice(NPC_KINDS),
                hp=rng.randint(5, 50),
            ))
            npc_id += 1

    return npcs


def random_place_loot(
    rooms: list[Room],
    occupied: set[tuple[int, int]],
    rng: random.Random,
) -> list[LootItem]:
    """Розміщує лут повністю випадково."""
    loot: list[LootItem] = []
    loot_id = 0

    for room in rooms:
        free = _free_positions(room, occupied)
        if not free:
            continue
        rng.shuffle(free)
        count = rng.randint(0, min(3, len(free)))
        for i in range(count):
            x, y = free[i]
            occupied.add((x, y))
            loot.append(LootItem(
                id=loot_id, room_id=room.id,
                x=x, y=y,
                kind=rng.choice(LOOT_KINDS),
                value=rng.randint(1, 20),
            ))
            loot_id += 1

    return loot