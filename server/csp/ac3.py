"""
AC-3 з підтримкою boss і merchant ізоляції в тупиках.
"""

from __future__ import annotations
from collections import deque
import random

from protocol import Room
from csp.constraints import (
    Constraint,
    GLOBAL_LIMITS,
    DEAD_END_ONLY_TYPES,
    BOSS_MAX_NEIGHBORS,
    initial_domain,
)


def ac3(
    rooms: list[Room],
    neighbors: dict[int, list[int]],
    rng: random.Random,
) -> dict[int, str]:
    # 1. Домени
    domains: dict[int, list[str]] = {
        room.id: initial_domain(room.id, len(rooms))
        for room in rooms
    }

    # 2. Boss і merchant — тільки тупики
    for room in rooms:
        nbr_count = len(neighbors.get(room.id, []))
        if nbr_count > BOSS_MAX_NEIGHBORS:
            for dead_end_type in DEAD_END_ONLY_TYPES:
                if dead_end_type in domains[room.id]:
                    domains[room.id].remove(dead_end_type)

    # 3. Constraints
    constraints: list[Constraint] = []
    for room_id, nbrs in neighbors.items():
        for nbr_id in nbrs:
            if room_id < nbr_id:
                constraints.append(Constraint(room_id, nbr_id))

    # 4. AC-3
    queue: deque[Constraint] = deque(constraints)
    queue.extend(Constraint(c.room_b, c.room_a) for c in constraints)

    while queue:
        arc = queue.popleft()
        if _revise(domains, arc):
            if not domains[arc.room_a]:
                domains[arc.room_a] = ["generic"]
            for nbr in neighbors.get(arc.room_a, []):
                if nbr != arc.room_b:
                    queue.append(Constraint(nbr, arc.room_a))

    # 5. Призначення
    return _assign(domains, rooms, neighbors, rng)


def _revise(domains: dict[int, list[str]], arc: Constraint) -> bool:
    revised = False
    to_remove = []
    for type_a in domains[arc.room_a]:
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
    neighbors: dict[int, list[int]],
    rng: random.Random,
) -> dict[int, str]:
    assignment: dict[int, str] = {}
    type_counts: dict[str, int] = {t: 0 for t in GLOBAL_LIMITS}

    # Кімнати з одним значенням (entrance)
    for room in rooms:
        if len(domains[room.id]) == 1:
            chosen = domains[room.id][0]
            assignment[room.id] = chosen
            type_counts[chosen] = type_counts.get(chosen, 0) + 1

    # Тупики — кандидати для boss і merchant
    dead_ends = [
        room.id for room in rooms
        if len(neighbors.get(room.id, [])) <= BOSS_MAX_NEIGHBORS
        and room.id not in assignment
    ]
    rng.shuffle(dead_ends)

    # Призначаємо boss і merchant різним тупикам
    for dead_end_type in ["boss", "merchant"]:
        max_c = GLOBAL_LIMITS.get(dead_end_type, (0, 0))[1]
        if max_c < 1:
            continue
        for room_id in dead_ends:
            if room_id in assignment:
                continue
            if dead_end_type in domains[room_id]:
                assignment[room_id] = dead_end_type
                type_counts[dead_end_type] = 1
                break

    # Решта кімнат
    for room in rooms:
        if room.id in assignment:
            continue

        domain = [
            t for t in domains[room.id]
            if t not in DEAD_END_ONLY_TYPES
        ]
        rng.shuffle(domain)

        chosen = "generic"
        for candidate in domain:
            _, max_c = GLOBAL_LIMITS.get(candidate, (0, 999))
            if type_counts.get(candidate, 0) < max_c:
                chosen = candidate
                break

        assignment[room.id] = chosen
        type_counts[chosen] = type_counts.get(chosen, 0) + 1

    # Мінімуми
    for room_type, (min_c, _) in GLOBAL_LIMITS.items():
        if type_counts.get(room_type, 0) < min_c:
            for room in rooms:
                if type_counts.get(room_type, 0) >= min_c:
                    break
                if assignment.get(room.id) == "generic":
                    assignment[room.id] = room_type
                    type_counts["generic"] = max(0, type_counts.get("generic", 1) - 1)
                    type_counts[room_type] = type_counts.get(room_type, 0) + 1

    return assignment


def build_neighbor_graph(corridors: list[dict]) -> dict[int, list[int]]:
    graph: dict[int, list[int]] = {}
    for corridor in corridors:
        a = corridor["from"]
        b = corridor["to"]
        graph.setdefault(a, []).append(b)
        graph.setdefault(b, []).append(a)
    return graph