"""
Метрики для оцінки якості данжену.
Використовується для наукового порівняння методів.
"""

from __future__ import annotations
import math
import time
from collections import defaultdict, deque
from protocol import Room, NPC, LootItem
from csp.constraints import INCOMPATIBLE_NEIGHBORS, GLOBAL_LIMITS


# ─── Структурні метрики ───────────────────────────────────────────────────────

def is_fully_connected(rooms: list[Room], corridors: list[dict]) -> bool:
    """Чи всі кімнати досяжні одна від одної."""
    if not rooms:
        return True

    graph: dict[int, list[int]] = defaultdict(list)
    for c in corridors:
        graph[c["from"]].append(c["to"])
        graph[c["to"]].append(c["from"])

    visited = set()
    queue = deque([rooms[0].id])
    while queue:
        node = queue.popleft()
        if node in visited:
            continue
        visited.add(node)
        for nb in graph[node]:
            if nb not in visited:
                queue.append(nb)

    return len(visited) == len(rooms)


def room_type_entropy(rooms: list[Room]) -> float:
    """
    Ентропія Шеннона розподілу типів кімнат.
    Вища ентропія = різноманітніший данжен.
    """
    counts: dict[str, int] = defaultdict(int)
    for room in rooms:
        counts[room.type] += 1

    total = len(rooms)
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def path_length_to_boss(rooms: list[Room], corridors: list[dict]) -> int:
    """
    Довжина найкоротшого шляху від entrance до boss (в кімнатах).
    -1 якщо boss або entrance не існує.
    """
    entrance = next((r for r in rooms if r.type == "entrance"), None)
    boss     = next((r for r in rooms if r.type == "boss"), None)

    if not entrance or not boss:
        return -1

    graph: dict[int, list[int]] = defaultdict(list)
    for c in corridors:
        graph[c["from"]].append(c["to"])
        graph[c["to"]].append(c["from"])

    # BFS
    visited = {entrance.id: 0}
    queue = deque([entrance.id])
    while queue:
        node = queue.popleft()
        if node == boss.id:
            return visited[node]
        for nb in graph[node]:
            if nb not in visited:
                visited[nb] = visited[node] + 1
                queue.append(nb)

    return -1  # boss недосяжний


# ─── Балансові метрики ────────────────────────────────────────────────────────

def count_constraint_violations(
    rooms: list[Room],
    corridors: list[dict],
    npcs: list[NPC],
    loot: list[LootItem],
) -> int:
    """
    Рахує кількість порушень constraints.
    Це головна метрика — AC-3 має давати 0.
    """
    violations = 0
    room_map = {r.id: r for r in rooms}

    # 1. Несумісні сусіди
    for c in corridors:
        ra = room_map.get(c["from"])
        rb = room_map.get(c["to"])
        if ra and rb:
            if rb.type in INCOMPATIBLE_NEIGHBORS.get(ra.type, []):
                violations += 1

    # 2. Глобальні ліміти
    type_counts: dict[str, int] = defaultdict(int)
    for r in rooms:
        type_counts[r.type] += 1

    for room_type, (min_c, max_c) in GLOBAL_LIMITS.items():
        count = type_counts.get(room_type, 0)
        if count < min_c or count > max_c:
            violations += 1

    # 3. Merchant кімната — не повинна мати лут
    merchant_rooms = {r.id for r in rooms if r.type == "merchant"}
    for item in loot:
        if item.room_id in merchant_rooms:
            violations += 1

    # 4. Boss кімната — не повинна мати лут
    boss_rooms = {r.id for r in rooms if r.type == "boss"}
    for item in loot:
        if item.room_id in boss_rooms:
            violations += 1

    # 5. Merchant кімната — тільки merchant NPC
    for npc in npcs:
        if npc.room_id in merchant_rooms and npc.kind != "merchant":
            violations += 1

    return violations


def npc_density_variance(rooms: list[Room], npcs: list[NPC]) -> float:
    """
    Дисперсія кількості NPC по кімнатах.
    Менша дисперсія = рівномірніший розподіл.
    """
    counts_per_room: dict[int, int] = defaultdict(int)
    for npc in npcs:
        counts_per_room[npc.room_id] += 1

    values = [counts_per_room.get(r.id, 0) for r in rooms]
    if not values:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return round(variance, 4)


def loot_rarity_gradient(
    rooms: list[Room],
    corridors: list[dict],
    loot: list[LootItem],
) -> float:
    """
    Кореляція Спірмена між глибиною кімнати (від entrance) і цінністю луту.
    Позитивна кореляція = складніші кімнати мають кращий лут (бажано).
    """
    entrance = next((r for r in rooms if r.type == "entrance"), None)
    if not entrance:
        return 0.0

    # BFS для глибини кожної кімнати
    graph: dict[int, list[int]] = defaultdict(list)
    for c in corridors:
        graph[c["from"]].append(c["to"])
        graph[c["to"]].append(c["from"])

    depth: dict[int, int] = {entrance.id: 0}
    queue = deque([entrance.id])
    while queue:
        node = queue.popleft()
        for nb in graph[node]:
            if nb not in depth:
                depth[nb] = depth[node] + 1
                queue.append(nb)

    # Середня цінність луту по кімнатах
    loot_by_room: dict[int, list[int]] = defaultdict(list)
    for item in loot:
        loot_by_room[item.room_id].append(item.value)

    room_depth_list = []
    room_loot_list  = []
    for room in rooms:
        if room.id in loot_by_room and room.id in depth:
            room_depth_list.append(depth[room.id])
            room_loot_list.append(sum(loot_by_room[room.id]) / len(loot_by_room[room.id]))

    if len(room_depth_list) < 3:
        return 0.0

    return round(_spearman(room_depth_list, room_loot_list), 4)


def _spearman(x: list[float], y: list[float]) -> float:
    """Кореляція Спірмена без scipy."""
    n = len(x)
    rx = _ranks(x)
    ry = _ranks(y)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - (6 * d2) / (n * (n ** 2 - 1))


def _ranks(data: list[float]) -> list[float]:
    sorted_data = sorted(enumerate(data), key=lambda x: x[1])
    ranks = [0.0] * len(data)
    for rank, (idx, _) in enumerate(sorted_data):
        ranks[idx] = rank + 1
    return ranks


# ─── Головна функція оцінки ───────────────────────────────────────────────────

def evaluate_dungeon(
    rooms: list[Room],
    corridors: list[dict],
    npcs: list[NPC],
    loot: list[LootItem],
    generation_time_ms: float = 0.0,
) -> dict:
    """
    Повертає повний набір метрик для одного данжену.
    """
    return {
        # Структурні
        "connectivity":            is_fully_connected(rooms, corridors),
        "room_type_entropy":       room_type_entropy(rooms),
        "path_length_to_boss":     path_length_to_boss(rooms, corridors),

        # Балансові
        "constraint_violations":   count_constraint_violations(rooms, corridors, npcs, loot),
        "npc_density_variance":    npc_density_variance(rooms, npcs),
        "loot_rarity_gradient":    loot_rarity_gradient(rooms, corridors, loot),

        # Технічні
        "generation_time_ms":      round(generation_time_ms, 2),
        "room_count":              len(rooms),
        "npc_count":               len(npcs),
        "loot_count":              len(loot),
    }