"""
Генератор графіків для результатів експерименту.

Запуск:
    python plot_results.py                        # читає experiment_results.csv
    python plot_results.py --input my_results.csv # кастомний файл
    python plot_results.py --show                 # показати графіки інтерактивно

Вихідні файли (папка charts/):
    01_constraint_violations_boxplot.png
    02_constraint_violations_by_size.png
    03_generation_time_boxplot.png
    04_generation_time_by_size.png
    05_room_type_entropy.png
    06_path_length_to_boss.png
    07_npc_density_variance.png
    08_loot_rarity_gradient.png
    09_scalability_time.png
    10_scalability_violations.png
    11_summary_table.png
"""

from __future__ import annotations
import argparse
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")   # без GUI — рендер в файл
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─── Константи ────────────────────────────────────────────────────────────────

METHODS = ["AC3Placer", "RandomPlacer", "GreedyPlacer"]
SIZES   = [10, 15, 20, 25, 30]
COLORS  = {
    "AC3Placer":    "#2ecc71",   # зелений
    "RandomPlacer": "#e74c3c",   # червоний
    "GreedyPlacer": "#3498db",   # синій
}
LABELS = {
    "AC3Placer":    "AC-3 (наш метод)",
    "RandomPlacer": "Випадковий",
    "GreedyPlacer": "Жадібний",
}
OUTPUT_DIR = "charts"


# ─── Завантаження даних ───────────────────────────────────────────────────────

def load_data(filepath: str) -> dict:
    """
    Завантажує CSV і повертає словник:
    {method: {metric: [values]}}
    і
    {method: {size: {metric: [values]}}}
    """
    rows: list[dict] = []
    with open(filepath, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Плоский словник по методах
    by_method: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    # По методу і розміру
    by_method_size: dict[str, dict[int, dict[str, list]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    numeric_fields = [
        "constraint_violations", "generation_time_ms", "room_type_entropy",
        "path_length_to_boss", "npc_density_variance", "loot_rarity_gradient",
        "room_count", "npc_count", "loot_count",
    ]

    for row in rows:
        method = row["method"]
        size   = int(row["size"])
        for field in numeric_fields:
            val = float(row.get(field, 0) or 0)
            by_method[method][field].append(val)
            by_method_size[method][size][field].append(val)

    return by_method, by_method_size


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = sum(values) / len(values)
    s = (sum((v - m) ** 2 for v in values) / len(values)) ** 0.5
    return m, s


# ─── Графіки ──────────────────────────────────────────────────────────────────

def plot_boxplot(
    by_method: dict,
    metric: str,
    title: str,
    ylabel: str,
    filename: str,
    show: bool = False,
) -> None:
    """
    Боксплот метрики по трьох методах.
    Показує медіану, квартилі, викиди.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    data   = [by_method[m][metric] for m in METHODS]
    colors = [COLORS[m] for m in METHODS]
    labels = [LABELS[m] for m in METHODS]

    bp = ax.boxplot(data, patch_artist=True, labels=labels, widths=0.5)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)

    # Додаємо середнє значення як мітку
    for i, (m, d) in enumerate(zip(METHODS, data), 1):
        mean, std = mean_std(d)
        ax.text(i, ax.get_ylim()[1] * 0.95,
                f"μ={mean:.2f}\nσ={std:.2f}",
                ha="center", fontsize=8, color="black",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))

    plt.tight_layout()
    _save(fig, filename, show)


def plot_by_size(
    by_method_size: dict,
    metric: str,
    title: str,
    ylabel: str,
    filename: str,
    show: bool = False,
) -> None:
    """
    Лінійний графік метрики по розмірах карти.
    Показує масштабованість методів.
    Включає довірчий інтервал (±1σ).
    """
    fig, ax = plt.subplots(figsize=(9, 5))

    for method in METHODS:
        means = []
        stds  = []
        for size in SIZES:
            vals = by_method_size[method][size][metric]
            m, s = mean_std(vals)
            means.append(m)
            stds.append(s)

        means_arr = np.array(means)
        stds_arr  = np.array(stds)

        ax.plot(SIZES, means_arr, marker="o", label=LABELS[method],
                color=COLORS[method], linewidth=2)
        ax.fill_between(SIZES,
                        means_arr - stds_arr,
                        means_arr + stds_arr,
                        alpha=0.15, color=COLORS[method])

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("Розмір карти (тайлів)")
    ax.set_ylabel(ylabel)
    ax.set_xticks(SIZES)
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    _save(fig, filename, show)


def plot_summary_table(by_method: dict, filename: str, show: bool = False) -> None:
    """
    Зведена таблиця всіх метрик у вигляді графіку.
    M ± SD для кожного методу і метрики.
    """
    metrics = [
        ("constraint_violations", "Порушень constraints"),
        ("generation_time_ms",    "Час генерації (мс)"),
        ("room_type_entropy",     "Ентропія типів кімнат"),
        ("path_length_to_boss",   "Відстань до Boss"),
        ("npc_density_variance",  "Дисперсія NPC"),
        ("loot_rarity_gradient",  "Градієнт луту (Спірмен)"),
    ]

    fig, ax = plt.subplots(figsize=(12, len(metrics) * 0.9 + 1.5))
    ax.axis("off")

    col_labels = ["Метрика"] + [LABELS[m] for m in METHODS]
    table_data = []

    for metric_key, metric_label in metrics:
        row = [metric_label]
        for method in METHODS:
            vals = by_method[method][metric_key]
            m, s = mean_std(vals)
            row.append(f"{m:.3f} ± {s:.3f}")
        table_data.append(row)

    table = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)

    # Кольорові заголовки методів
    for j, method in enumerate(METHODS, 1):
        table[0, j].set_facecolor(COLORS[method])
        table[0, j].set_text_props(color="white", fontweight="bold")

    # Сіре підсвічування кожного другого рядка
    for i in range(1, len(metrics) + 1):
        if i % 2 == 0:
            for j in range(len(col_labels)):
                table[i, j].set_facecolor("#f0f0f0")

    ax.set_title("Зведена таблиця метрик (M ± SD)",
                 fontsize=13, fontweight="bold", pad=20)
    plt.tight_layout()
    _save(fig, filename, show)


def plot_cliffs_delta(by_method: dict, filename: str, show: bool = False) -> None:
    """
    Горизонтальний барчарт розміру ефекту Кліффа (AC-3 vs інші).
    Показує практичну значущість різниці між методами.
    """
    metrics = [
        ("constraint_violations", "Порушень constraints"),
        ("generation_time_ms",    "Час генерації"),
        ("room_type_entropy",     "Ентропія типів"),
        ("npc_density_variance",  "Дисперсія NPC"),
    ]
    comparison_methods = ["RandomPlacer", "GreedyPlacer"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, comp_method in zip(axes, comparison_methods):
        ac3_data = by_method["AC3Placer"]
        comp_data = by_method[comp_method]

        deltas = []
        labels = []
        for metric_key, metric_label in metrics:
            a = ac3_data[metric_key]
            b = comp_data[metric_key]
            d = _cliffs_delta(a, b)
            deltas.append(d)
            labels.append(metric_label)

        colors_bar = ["#2ecc71" if d < 0 else "#e74c3c" for d in deltas]
        bars = ax.barh(labels, deltas, color=colors_bar, alpha=0.7)

        # Порогові лінії
        for threshold, label in [(0.147, "малий"), (0.33, "середній"), (0.474, "великий")]:
            ax.axvline(x=threshold,  color="gray", linestyle="--", alpha=0.5, linewidth=0.8)
            ax.axvline(x=-threshold, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)

        ax.axvline(x=0, color="black", linewidth=1)
        ax.set_xlim(-1, 1)
        ax.set_title(f"Cliff's δ: AC-3 vs {LABELS[comp_method]}",
                     fontsize=11, fontweight="bold")
        ax.set_xlabel("Cliff's delta (від -1 до 1)")
        ax.grid(axis="x", alpha=0.3)

        # Підписи значень
        for bar, d in zip(bars, deltas):
            ax.text(d + (0.03 if d >= 0 else -0.03), bar.get_y() + bar.get_height()/2,
                    f"{d:.3f}", va="center", ha="left" if d >= 0 else "right", fontsize=9)

    plt.suptitle("Розмір ефекту Кліффа\n(від'ємне = AC-3 менше = краще для violations/variance)",
                 fontsize=12)
    plt.tight_layout()
    _save(fig, filename, show)


def _cliffs_delta(a: list[float], b: list[float]) -> float:
    n = len(a) * len(b)
    if n == 0:
        return 0.0
    # Для великих списків — семплінг щоб не зависати
    if n > 100_000:
        import random
        a = random.sample(a, min(500, len(a)))
        b = random.sample(b, min(500, len(b)))
        n = len(a) * len(b)
    result = sum(1 if x > y else (-1 if x < y else 0) for x in a for y in b)
    return round(result / n, 4)


# ─── Утиліти ──────────────────────────────────────────────────────────────────

def _save(fig, filename: str, show: bool) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  збережено: {path}")
    if show:
        plt.show()
    plt.close(fig)


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Побудова графіків експерименту")
    parser.add_argument("--input", default="experiment_results.csv")
    parser.add_argument("--show",  action="store_true", help="показати інтерактивно")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Файл {args.input} не знайдено. Спочатку запусти experiment.py")
        return

    print(f"Завантаження {args.input}...")
    by_method, by_method_size = load_data(args.input)
    print(f"Побудова графіків → папка '{OUTPUT_DIR}/':\n")

    # 1. Боксплот порушень
    plot_boxplot(by_method,
        "constraint_violations",
        "Кількість порушень constraints",
        "Кількість порушень",
        "01_constraint_violations_boxplot.png", args.show)

    # 2. Порушення по розмірах
    plot_by_size(by_method_size,
        "constraint_violations",
        "Порушення constraints залежно від розміру карти",
        "Середня кількість порушень",
        "02_constraint_violations_by_size.png", args.show)

    # 3. Боксплот часу генерації
    plot_boxplot(by_method,
        "generation_time_ms",
        "Час генерації данжену",
        "Час (мс)",
        "03_generation_time_boxplot.png", args.show)

    # 4. Час по розмірах (масштабованість)
    plot_by_size(by_method_size,
        "generation_time_ms",
        "Масштабованість: час генерації по розміру карти",
        "Час (мс)",
        "04_generation_time_by_size.png", args.show)

    # 5. Ентропія типів кімнат
    plot_boxplot(by_method,
        "room_type_entropy",
        "Різноманітність типів кімнат (ентропія Шеннона)",
        "Ентропія (біт)",
        "05_room_type_entropy.png", args.show)

    # 6. Відстань до boss
    plot_boxplot(by_method,
        "path_length_to_boss",
        "Довжина шляху від Entrance до Boss",
        "Кількість кімнат",
        "06_path_length_to_boss.png", args.show)

    # 7. Дисперсія NPC
    plot_boxplot(by_method,
        "npc_density_variance",
        "Рівномірність розподілу NPC по кімнатах",
        "Дисперсія",
        "07_npc_density_variance.png", args.show)

    # 8. Градієнт луту
    plot_boxplot(by_method,
        "loot_rarity_gradient",
        "Градієнт складності: лут і глибина кімнати (ρ Спірмена)",
        "Кореляція Спірмена",
        "08_loot_rarity_gradient.png", args.show)

    # 9-10. Масштабованість
    plot_by_size(by_method_size,
        "generation_time_ms",
        "Масштабованість часу генерації",
        "Час (мс)",
        "09_scalability_time.png", args.show)

    plot_by_size(by_method_size,
        "constraint_violations",
        "Масштабованість порушень constraints",
        "Порушень",
        "10_scalability_violations.png", args.show)

    # 11. Зведена таблиця
    plot_summary_table(by_method,
        "11_summary_table.png", args.show)

    # 12. Cliff's delta
    plot_cliffs_delta(by_method,
        "12_cliffs_delta.png", args.show)

    print(f"\nВсього збережено {len(os.listdir(OUTPUT_DIR))} графіків у папку '{OUTPUT_DIR}/'")


if __name__ == "__main__":
    main()