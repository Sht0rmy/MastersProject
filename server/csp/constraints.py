"""
Constraints для данжену.
"""

from __future__ import annotations
from dataclasses import dataclass

ROOM_TYPES = ["entrance", "combat", "treasure", "boss", "generic", "merchant"]

GLOBAL_LIMITS: dict[str, tuple[int, int]] = {
    "entrance": (1, 1),
    "boss":     (0, 1),
    "merchant": (0, 1),    # рівно 0 або 1 merchant
    "treasure": (1, 3),
    "combat":   (2, 999),
    "generic":  (0, 999),
}

INCOMPATIBLE_NEIGHBORS: dict[str, list[str]] = {
    "entrance": ["boss", "treasure"],
    "boss":     ["entrance", "treasure", "boss", "merchant"],
    "treasure": ["entrance", "boss"],
    "merchant": ["boss"],   # merchant не може межувати з boss
    "combat":   [],
    "generic":  [],
}

# Boss і merchant — тільки тупики (1 сусід)
DEAD_END_ONLY_TYPES = {"boss", "merchant"}
BOSS_MAX_NEIGHBORS = 1


def initial_domain(room_id: int, total_rooms: int) -> list[str]:
    if room_id == 0:
        return ["entrance"]
    return ["combat", "treasure", "boss", "generic", "merchant"]


@dataclass
class Constraint:
    room_a: int
    room_b: int

    def is_satisfied(self, type_a: str, type_b: str) -> bool:
        if type_b in INCOMPATIBLE_NEIGHBORS.get(type_a, []):
            return False
        if type_a in INCOMPATIBLE_NEIGHBORS.get(type_b, []):
            return False
        return True