"""
AC-3 (Arc Consistency Algorithm 3).

Алгоритм:
1. Починаємо з початкових доменів для кожної кімнати
2. Для кожної пари сусідніх кімнат (arc) перевіряємо сумісність
3. Якщо значення в домені A не має жодного сумісного значення в домені B — видаляємо його
4. Якщо домен змінився — додаємо всі суміжні арки в чергу
5. Повторюємо поки черга не порожня

Результат: звужені домени → вибираємо тип для кожної кімнати.
"""

from __future__ import annotations
from collections import deque
import random

from protocol import Room
from csp.constraints import (
    Constraint,
    GLOBAL_LIMITS,
    initial_domain,
)


# ─── AC-3 ─────────────────────────────────────────────────────────────────────

def ac3(
    rooms: list[Room],
    neighbors: dict[int, list[int]],
    rng: random.Random,
) -> dict[int, str]:
    """
    Запускає AC-3 і повертає призначення типів {room_id: type}.

    Args:
        rooms:     список кімнат
        neighbors: граф суміжності {room_id: [room_id, ...]}
        rng:       генератор випадкових чисел
    """
    # 1. Ініціалізуємо домени
    domains: dict[int, list[str]] = {
        room.id: initial_domain(room.id, len(rooms))
        for room in rooms
    }

    # 2. Будуємо список constraints (арок)
    constraints: list[Constraint] = []
    for room_id, nbrs in neighbors.items():
        for nbr_id in nbrs:
            if room_id < nbr_id:  # уникаємо дублікатів
                constraints.append(Constraint(room_id, nbr_id))

    # 3. AC-3
    queue: deque[Constraint] = deque(constraints)
    # Також додаємо зворотні арки
    queue.extend(Constraint(c.room_b, c.room_a) for c in constraints)

    while queue:
        arc = queue.popleft()
        if _revise(domains, arc):
            if not domains[arc.room_a]:
                # Домен порожній — відновлюємо до generic
                domains[arc.room_a] = ["generic"]
            # Додаємо сусідів в чергу
            for nbr in neighbors.get(arc.room_a, []):
                if nbr != arc.room_b:
                    queue.append(Constraint(nbr, arc.room_a))

    # 4. Вибираємо тип з домену для кожної кімнати
    assignment = _assign(domains, rooms, rng)
    return assignment


def _revise(domains: dict[int, list[str]], arc: Constraint) -> bool:
    """
    Видаляє з домену arc.room_a значення які не мають
    жодного сумісного значення в домені arc.room_b.
    Повертає True якщо домен змінився.
    """
    revised = False
    to_remove = []

    for type_a in domains[arc.room_a]:
        # Чи є хоч одне сумісне значення в домені B?
        has_support = any(
            arc.is_satisfied(type_a, type_b)
            for type_b in domains[arc.room_b]
        )
        if not has_support:
            to_remove.append(type_a)
            revised = True

    for t in to_remove:
        domains[arc.room_a].remove(t)

    return revised


def _assign(
    domains: dict[int, list[str]],
    rooms: list[Room],
    rng: random.Random,
) -> dict[int, str]:
    """
    Вибирає тип для кожної кімнати з домену
    з урахуванням глобальних лімітів.
    """
    assignment: dict[int, str] = {}
    type_counts: dict[str, int] = {t: 0 for t in GLOBAL_LIMITS}

    # Спочатку призначаємо кімнати з одним значенням в домені (entrance)
    for room in rooms:
        domain = domains[room.id]
        if len(domain) == 1:
            chosen = domain[0]
            assignment[room.id] = chosen
            type_counts[chosen] = type_counts.get(chosen, 0) + 1

    # Потім решту — з урахуванням лімітів
    for room in rooms:
        if room.id in assignment:
            continue

        domain = list(domains[room.id])
        rng.shuffle(domain)

        chosen = "generic"
        for candidate in domain:
            min_c, max_c = GLOBAL_LIMITS.get(candidate, (0, 999))
            current = type_counts.get(candidate, 0)

            # Перевіряємо чи не перевищено максимум
            if current < max_c:
                chosen = candidate
                break

        assignment[room.id] = chosen
        type_counts[chosen] = type_counts.get(chosen, 0) + 1

    # Перевіряємо мінімуми — якщо якийсь тип не досягнув мінімуму,
    # перепризначаємо generic кімнати
    for room_type, (min_c, _) in GLOBAL_LIMITS.items():
        current = type_counts.get(room_type, 0)
        if current < min_c:
            # Знаходимо generic кімнати і перепризначаємо
            for room in rooms:
                if type_counts.get(room_type, 0) >= min_c:
                    break
                if assignment.get(room.id) == "generic":
                    assignment[room.id] = room_type
                    type_counts["generic"] = type_counts.get("generic", 1) - 1
                    type_counts[room_type] = type_counts.get(room_type, 0) + 1

    return assignment


# ─── Граф суміжності з коридорів ──────────────────────────────────────────────

def build_neighbor_graph(corridors: list[dict]) -> dict[int, list[int]]:
    """Будує граф суміжності кімнат з списку коридорів."""
    graph: dict[int, list[int]] = {}

    for corridor in corridors:
        a = corridor["from"]
        b = corridor["to"]
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)

    return graph