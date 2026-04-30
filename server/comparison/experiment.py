"""
Експериментальний runner для порівняння методів розміщення.

Запуск:
    python experiment.py                    # повний експеримент (1000 seeds)
    python experiment.py --quick            # швидкий тест (50 seeds)
    python experiment.py --seeds 100        # кастомна кількість seeds
"""

from __future__ import annotations
import argparse
import csv
import random
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol import Room, NPC, LootItem
from dungeon import generate_bsp, build_corridors
from placement import place_npcs, place_loot
from csp import ac3, build_neighbor_graph
from comparison.random_placer import random_place_npcs, random_place_loot
from comparison.greedy_placer import greedy_place_npcs, greedy_place_loot
from comparison.metrics import evaluate_dungeon

# ─── Протокол експерименту ────────────────────────────────────────────────────

SEEDS = list(range(1000))
SIZES = [20, 30, 40, 50, 60]
METHODS = ["AC3Placer", "RandomPlacer", "GreedyPlacer"]

OUTPUT_FILE = "experiment_results.csv"


# ─── Методи генерації ─────────────────────────────────────────────────────────

def generate_ac3(seed: int, size: int) -> tuple:
    rng = random.Random(seed)
    result = generate_bsp(size=size, seed=seed)
    corridors = build_corridors(result.pairs, grid_w=size, grid_h=size, rooms=result.rooms)
    neighbor_graph = build_neighbor_graph(corridors)
    room_types = ac3(result.rooms, neighbor_graph, rng)
    for room in result.rooms:
        room.type = room_types.get(room.id, "generic")
    npcs = place_npcs(result.rooms, rng)
    occupied = {(n.x, n.y) for n in npcs}
    loot = place_loot(result.rooms, occupied, rng)
    return result.rooms, corridors, npcs, loot


def generate_random(seed: int, size: int) -> tuple:
    rng = random.Random(seed)
    result = generate_bsp(size=size, seed=seed)
    corridors = build_corridors(result.pairs, grid_w=size, grid_h=size, rooms=result.rooms)
    # Без AC-3 — типи кімнат залишаються як після BSP (випадкові)
    npcs = random_place_npcs(result.rooms, rng)
    occupied = {(n.x, n.y) for n in npcs}
    loot = random_place_loot(result.rooms, occupied, rng)
    return result.rooms, corridors, npcs, loot


def generate_greedy(seed: int, size: int) -> tuple:
    rng = random.Random(seed)
    result = generate_bsp(size=size, seed=seed)
    corridors = build_corridors(result.pairs, grid_w=size, grid_h=size, rooms=result.rooms)
    # Без AC-3 — типи як після BSP
    npcs = greedy_place_npcs(result.rooms, rng)
    occupied = {(n.x, n.y) for n in npcs}
    loot = greedy_place_loot(result.rooms, occupied, rng)
    return result.rooms, corridors, npcs, loot


METHOD_FN = {
    "AC3Placer":    generate_ac3,
    "RandomPlacer": generate_random,
    "GreedyPlacer": generate_greedy,
}


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_experiment(seeds: list[int], sizes: list[int], output: str) -> None:
    total = len(METHODS) * len(sizes) * len(seeds)
    done  = 0

    with open(output, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "method", "size", "seed",
            "connectivity", "room_type_entropy", "path_length_to_boss",
            "constraint_violations", "npc_density_variance", "loot_rarity_gradient",
            "generation_time_ms", "room_count", "npc_count", "loot_count",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for method_name in METHODS:
            fn = METHOD_FN[method_name]
            for size in sizes:
                for seed in seeds:
                    try:
                        t0 = time.perf_counter()
                        rooms, corridors, npcs, loot = fn(seed, size)
                        elapsed_ms = (time.perf_counter() - t0) * 1000

                        metrics = evaluate_dungeon(rooms, corridors, npcs, loot, elapsed_ms)
                        row = {"method": method_name, "size": size, "seed": seed, **metrics}
                        writer.writerow(row)

                    except Exception as e:
                        # Записуємо failed генерацію
                        writer.writerow({
                            "method": method_name, "size": size, "seed": seed,
                            "connectivity": False, "room_type_entropy": 0,
                            "path_length_to_boss": -1, "constraint_violations": 999,
                            "npc_density_variance": 0, "loot_rarity_gradient": 0,
                            "generation_time_ms": 0, "room_count": 0,
                            "npc_count": 0, "loot_count": 0,
                        })

                    done += 1
                    if done % 500 == 0 or done == total:
                        pct = done / total * 100
                        print(f"  [{pct:5.1f}%] {done}/{total} — {method_name} size={size}", flush=True)

    print(f"\nГотово. Результати збережено в {output}")


# ─── Статистика (без scipy) ───────────────────────────────────────────────────

def print_summary(output: str) -> None:
    import csv
    from collections import defaultdict

    rows: list[dict] = []
    with open(output, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Групуємо по методу
    by_method: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)

    print("\n" + "=" * 70)
    print(f"{'Метод':<16} {'Порушення M±SD':<20} {'Час мс M±SD':<20} {'Ентропія':<12}")
    print("=" * 70)

    for method in METHODS:
        data = by_method[method]
        violations = [float(r["constraint_violations"]) for r in data]
        times       = [float(r["generation_time_ms"]) for r in data]
        entropy     = [float(r["room_type_entropy"]) for r in data]

        def mean_std(vals):
            m = sum(vals) / len(vals)
            s = (sum((v - m)**2 for v in vals) / len(vals)) ** 0.5
            return m, s

        mv, sv = mean_std(violations)
        mt, st = mean_std(times)
        me, _  = mean_std(entropy)

        print(f"{method:<16} {mv:.2f} ± {sv:.2f}{'':>8} {mt:.1f} ± {st:.1f}{'':>6} {me:.3f}")

    print("=" * 70)

    # Mann-Whitney U (спрощена версія без scipy)
    print("\nМанн-Уітні (порушення, AC3 vs інші):")
    ac3_v = [float(r["constraint_violations"]) for r in by_method["AC3Placer"]]
    for method in ["RandomPlacer", "GreedyPlacer"]:
        other_v = [float(r["constraint_violations"]) for r in by_method[method]]
        u, n1, n2 = 0, len(ac3_v), len(other_v)
        for a in ac3_v:
            for b in other_v:
                if a < b: u += 1
                elif a == b: u += 0.5
        # Нормалізований U
        u_norm = u / (n1 * n2)
        d = cliffs_delta(ac3_v, other_v)
        print(f"  AC3 vs {method}: U_norm={u_norm:.4f}, Cliff's d={d:.4f}")


def cliffs_delta(a: list[float], b: list[float]) -> float:
    n = len(a) * len(b)
    if n == 0:
        return 0.0
    result = sum(1 if x > y else (-1 if x < y else 0) for x in a for y in b)
    return round(result / n, 4)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dungeon generation experiment")
    parser.add_argument("--quick",  action="store_true", help="50 seeds замість 1000")
    parser.add_argument("--seeds",  type=int, default=None, help="кількість seeds")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE)
    args = parser.parse_args()

    if args.quick:
        seeds = list(range(50))
    elif args.seeds:
        seeds = list(range(args.seeds))
    else:
        seeds = SEEDS

    print(f"Запуск експерименту: {len(METHODS)} методи × {len(SIZES)} розміри × {len(seeds)} seeds")
    print(f"Всього запусків: {len(METHODS) * len(SIZES) * len(seeds)}")
    print(f"Вивід: {args.output}\n")

    run_experiment(seeds, SIZES, args.output)
    print_summary(args.output)