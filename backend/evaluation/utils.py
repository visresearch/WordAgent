"""
Evaluation utilities: CSV reading and plotting.
"""

import csv
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


def read_csv(csv_path: Path) -> List[Dict[str, str]]:
    """Read evaluation results from CSV file."""
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def aggregate_by_model(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """
    Read CSV and compute average quality metrics per model.
    Only includes data where task_completion=1.

    Returns:
        Dict[model_name, Dict[metric_name, avg_value]]
    """
    results = read_csv(csv_path)
    if not results:
        return {}

    model_data: Dict[str, List[Dict]] = {}
    for row in results:
        model = row.get("model", "unknown")
        model_data.setdefault(model, []).append(row)

    aggregated = {}
    metrics = ["clarity", "naturalness", "conciseness", "redundancy"]

    for model, rows in model_data.items():
        agg = {}
        completed_rows = [row for row in rows if row.get("task_completion") == "1"]
        for metric in metrics:
            values = []
            for row in completed_rows:
                val = row.get(metric, "")
                if val is not None and val != "":
                    try:
                        values.append(float(val))
                    except ValueError:
                        pass
            if values:
                agg[metric] = sum(values) / len(values)
            else:
                agg[metric] = 0.0

        aggregated[model] = agg

    return aggregated


def aggregate_task_completion_by_model(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """
    Read CSV and compute task_completion rate per model.

    Returns:
        Dict[model_name, {"task_completion": rate_0_to_100}]
    """
    results = read_csv(csv_path)
    if not results:
        return {}

    model_data: Dict[str, List[Dict]] = {}
    for row in results:
        model = row.get("model", "unknown")
        model_data.setdefault(model, []).append(row)

    aggregated = {}

    for model, rows in model_data.items():
        total = len(rows)
        completed = sum(1 for row in rows if row.get("task_completion") == "1")
        rate = (completed / total * 100) if total > 0 else 0.0
        aggregated[model] = {"task_completion": rate, "completed_count": completed, "total_count": total}

    return aggregated


def plot_task_completion(csv_path: Path, output_path: Path | None = None):
    """
    Plot task completion rate per model as a single bar chart.

    Args:
        csv_path: Path to the summary CSV file
        output_path: Optional path to save the figure; if None, displays interactively
    """
    aggregated = aggregate_task_completion_by_model(csv_path)
    if not aggregated:
        print("No data to plot.")
        return

    models = list(aggregated.keys())
    values = [aggregated[model]["task_completion"] for model in models]
    completed_counts = [aggregated[model]["completed_count"] for model in models]
    total_counts = [aggregated[model]["total_count"] for model in models]

    n_models = len(models)
    colors = plt.cm.Set2(np.linspace(0, 1, max(n_models, 8)))

    fig, ax = plt.subplots(figsize=(max(6, n_models * 1.5 + 2), 5))

    bars = ax.bar(models, values, color=colors[:n_models])

    for bar, val, completed, total in zip(bars, values, completed_counts, total_counts):
        height = bar.get_height()
        ax.annotate(
            f"{val:.1f}%\n({completed}/{total})",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xlabel("Model")
    ax.set_ylabel("Task Completion Rate (%)")
    ax.set_title("Task Completion Rate by Model")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {output_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_quality_metrics(csv_path: Path, output_path: Path | None = None):
    """
    Plot quality metrics (clarity, naturalness, conciseness, redundancy) per model.
    Only includes data where task_completion=1.

    Args:
        csv_path: Path to the summary CSV file
        output_path: Optional path to save the figure; if None, displays interactively
    """
    aggregated = aggregate_by_model(csv_path)
    if not aggregated:
        print("No data to plot.")
        return

    models = list(aggregated.keys())
    metrics = ["clarity", "naturalness", "conciseness", "redundancy"]

    n_models = len(models)
    n_metrics = len(metrics)
    bar_width = 0.12
    x = np.arange(n_metrics)

    colors = plt.cm.Set2(np.linspace(0, 1, max(n_models, 8)))

    fig, ax = plt.subplots(figsize=(max(10, n_metrics * 2 + 4), 6))

    for i, model in enumerate(models):
        values = [aggregated[model].get(m, 0) for m in metrics]
        offset = (i - n_models / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, values, bar_width, label=model, color=colors[i])

        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.annotate(
                f"{val:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_xlabel("Metrics")
    ax.set_ylabel("Score")
    ax.set_title("Quality Metrics by Model (task_completion=1 only)")
    ax.set_xticks(x)
    ax.set_xticklabels([
        "Clarity\n(0-5)", "Naturalness\n(0-5)",
        "Conciseness\n(0-5)", "Redundancy\n(0-5)"
    ])
    ax.legend(loc="upper right", bbox_to_anchor=(1.15, 1))
    ax.set_ylim(0, 6)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {output_path}")
    else:
        plt.show()

    plt.close(fig)
