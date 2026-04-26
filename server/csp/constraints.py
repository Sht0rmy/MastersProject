"""
Constraints для данжену.

Визначає правила які повинні виконуватись між кімнатами:
- Які типи кімнат можуть бути сусідами
- Скільки кімнат кожного типу може бути в данжені
- Які типи несумісні
"""

from __future__ import annotations
from dataclasses import dataclass

# ─── Типи кімнат ──────────────────────────────────────────────────────────────

ROOM_TYPES = ["entrance", "combat", "treasure", "boss", "generic"]

# ─── Глобальні обмеження (скільки кімнат кожного типу) ───────────────────────

GLOBAL_LIMITS: dict[str, tuple[int, int]] = {
    "entrance": (1, 1),    # рівно 1
    "boss":     (0, 1),    # не більше 1
    "treasure": (1, 3),    # від 1 до 3
    "combat":   (2, 999),  # мінімум 2
    "generic":  (0, 999),  # без обмежень
}

# ─── Обмеження на сусідство (які типи НЕ можуть бути поруч) ──────────────────

# Якщо A в списку B — A і B не можуть бути сусідами
INCOMPATIBLE_NEIGHBORS: dict[str, list[str]] = {
    "entrance": ["boss", "treasure"],   # вхід не може вести одразу до boss/скарбниці
    "boss":     ["entrance", "treasure"],
    "treasure": ["entrance", "boss"],
    "combat":   [],
    "generic":  [],
}

# ─── Домени (можливі типи для кожної кімнати) ─────────────────────────────────

def initial_domain(room_id: int, total_rooms: int) -> list[str]:
    """Початковий домен для кімнати — всі типи крім entrance (тільки кімната 0)."""
    if room_id == 0:
        return ["entrance"]
    return ["combat", "treasure", "boss", "generic"]


@dataclass
class Constraint:
    """Бінарний constraint між двома кімнатами."""
    room_a: int
    room_b: int

    def is_satisfied(self, type_a: str, type_b: str) -> bool:
        """Перевіряє чи сумісні два типи кімнат як сусіди."""
        if type_b in INCOMPATIBLE_NEIGHBORS.get(type_a, []):
            return False
        if type_a in INCOMPATIBLE_NEIGHBORS.get(type_b, []):
            return False
        return True