"""
Evaluation utilities: CSV reading, aggregation, and plotting.
"""

import csv
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

# 设置样式
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


# ===== 数据读取 =====


def read_csv(csv_path: Path) -> List[Dict[str, str]]:
    """Read evaluation results from CSV file."""
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def _parse_float(val: str) -> float:
    """Parse float value from string, handling percentage strings."""
    val = val.strip().replace("%", "")
    try:
        return float(val)
    except ValueError:
        return 0.0


def _parse_int(val: str) -> int:
    """Parse int value from string."""
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


# ===== 数据聚合 =====


def aggregate_metrics(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """
    Read CSV and compute average metrics per model.

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
    quality_metrics = ["correctness", "faithfulness", "relevance", "clarity", "conciseness"]
    all_metrics = quality_metrics + ["tool_usage"]

    for model, rows in model_data.items():
        agg = {}
        for metric in all_metrics:
            values = [_parse_float(row.get(metric, "")) for row in rows]
            agg[metric] = sum(values) / len(values) if values else 0.0
        aggregated[model] = agg

    return aggregated


def aggregate_task_success(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """
    Read CSV and compute task_success rate per model.

    Returns:
        Dict[model_name, {"task_success_rate": rate_0_to_100, "count": n}]
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
        successful = sum(1 for row in rows if _parse_int(row.get("task_success", "")) == 1)
        aggregated[model] = {
            "task_success_rate": successful / total * 100 if total > 0 else 0.0,
            "completed_count": successful,
            "total_count": total,
        }

    return aggregated


# ===== 绘图函数 =====


def _get_colors(n: int) -> List:
    """Get color palette using matplotlib's default cycle."""
    return plt.rcParams["axes.prop_cycle"].by_key()["color"][:n]


def plot_task_success(csv_path: Path, output_path: Path | None = None):
    """
    Plot task success rate per model as a bar chart.

    Args:
        csv_path: Path to the summary CSV file
        output_path: Optional path to save the figure
    """
    aggregated = aggregate_task_success(csv_path)
    if not aggregated:
        print("No data to plot.")
        return

    models = list(aggregated.keys())
    values = [aggregated[model]["task_success_rate"] for model in models]
    counts = [aggregated[model]["completed_count"] for model in models]
    totals = [aggregated[model]["total_count"] for model in models]

    n_models = len(models)
    fig, ax = plt.subplots(figsize=(max(6, n_models * 2 + 2), 5))

    colors = _get_colors(n_models)
    bars = ax.bar(models, values, color=colors)

    for bar, val, completed, total in zip(bars, values, counts, totals):
        height = bar.get_height()
        ax.annotate(
            f"{val:.1f}%\n({completed}/{total})",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_xlabel("Model", fontsize=12)
    ax.set_ylabel("Task Success Rate (%)", fontsize=12)
    ax.set_title("Task Success Rate by Model", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {output_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_quality_with_tool_usage(csv_path: Path, output_path: Path | None = None):
    """
    Plot quality metrics + tool usage per model as grouped bar chart.
    Uses dual Y-axes: left for quality metrics (0-5), right for tool usage (0-2).

    Args:
        csv_path: Path to the summary CSV file
        output_path: Optional path to save the figure
    """
    aggregated = aggregate_metrics(csv_path)
    if not aggregated:
        print("No data to plot.")
        return

    models = list(aggregated.keys())

    # Quality metrics (0-5 scale)
    quality_metrics = ["correctness", "faithfulness", "relevance", "clarity", "conciseness"]
    quality_labels = ["Correctness", "Faithfulness", "Relevance", "Clarity", "Conciseness"]
    # Tool usage (0-2 scale)
    tool_metrics = ["tool_usage"]
    tool_labels = ["Tool Usage"]

    n_models = len(models)
    bar_width = 0.12

    # X positions: quality metrics first, then tool usage with a gap
    n_quality = len(quality_metrics)
    quality_x = np.arange(n_quality)
    # Tool usage positioned after a small gap
    tool_x = np.array([n_quality + 0.5])  # Single position for tool usage

    colors = _get_colors(n_models)

    fig, ax1 = plt.subplots(figsize=(14, 6))
    ax2 = ax1.twinx()  # Secondary y-axis for tool usage

    # Plot quality metrics (left axis, 0-5 scale)
    for i, model in enumerate(models):
        values = []
        for m in quality_metrics:
            val = aggregated[model].get(m, 0)
            values.append(val)

        offset = (i - n_models / 2 + 0.5) * bar_width
        bars = ax1.bar(quality_x + offset, values, bar_width, label=model, color=colors[i])

        for bar, val in zip(bars, values):
            if val == int(val):
                label = f"{int(val)}"
            else:
                label = f"{val:.1f}"
            ax1.annotate(
                label,
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # Plot tool usage (right axis, 0-2 scale)
    for i, model in enumerate(models):
        val = aggregated[model].get("tool_usage", 0)
        offset = (i - n_models / 2 + 0.5) * bar_width
        bars = ax2.bar(tool_x[0] + offset, val, bar_width, color=colors[i])

        for bar in bars:
            if val == int(val):
                label = f"{int(val)}"
            else:
                label = f"{val:.1f}"
            ax2.annotate(
                label,
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # Set labels and title
    all_labels = quality_labels + tool_labels
    all_ticks = list(quality_x) + [tool_x[0]]
    ax1.set_xlabel("Metrics", fontsize=12)
    ax1.set_ylabel("Quality Score (0-5)", fontsize=12, color="black")
    ax2.set_ylabel("Tool Usage Score (0-2)", fontsize=12, color="black")
    ax1.set_title("Quality Metrics & Tool Usage by Model", fontsize=14, fontweight="bold")

    ax1.set_xticks(all_ticks)
    ax1.set_xticklabels(all_labels, fontsize=10)
    ax1.set_ylim(0, 5.5)
    ax1.set_yticks([0, 1, 2, 3, 4, 5])
    ax1.tick_params(axis="y", labelcolor="black")
    ax1.grid(axis="y", alpha=0.3)

    ax2.set_ylim(0, 2.2)
    ax2.set_yticks([0, 1, 2])
    # Force the right axis ticks to show 0, 1, 2
    ax2.set_yticklabels(["0", "1", "2"])
    ax2.tick_params(axis="y", labelcolor="black")

    ax1.legend(loc="upper left", fontsize=9)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {output_path}")
    else:
        plt.show()

    plt.close(fig)


def plot_radar_chart(csv_path: Path, output_path: Path | None = None):
    """
    Plot quality metrics as radar chart (spider chart) per model.
    All metrics normalized to 0-1 scale.

    Args:
        csv_path: Path to the summary CSV file
        output_path: Optional path to save the figure
    """
    aggregated = aggregate_metrics(csv_path)
    if not aggregated:
        print("No data to plot.")
        return

    models = list(aggregated.keys())
    metrics = ["Correctness", "Faithfulness", "Relevance", "Clarity", "Conciseness", "Tool Usage"]
    metric_keys = ["correctness", "faithfulness", "relevance", "clarity", "conciseness", "tool_usage"]

    n_models = len(models)
    colors = _get_colors(n_models)

    n_rings = 5  # 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))

    # Draw concentric circle grids (dashed) and radial lines
    for val in [i * 0.2 for i in range(n_rings + 1)]:
        circle_angles = np.linspace(0, 2 * np.pi, 200)
        ax.plot(circle_angles, [val] * len(circle_angles), "--", color="grey", linewidth=0.6, alpha=0.5)
    for angle in angles:
        ax.plot([angle, angle], [0, 1], "-", color="grey", linewidth=0.4, alpha=0.4)

    # Ring labels on the right side
    for val in [0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.text(np.pi / 2, val + 0.03, f"{val:.1f}", fontsize=9, ha="left", va="bottom", color="grey")

    # Plot data: normalize all metrics to 0-1
    for i, model in enumerate(models):
        values = []
        for m in metric_keys:
            val = aggregated[model].get(m, 0)
            # Quality metrics (0-5) -> 0-1
            if m != "tool_usage":
                val = val / 5.0
            # tool_usage (0-2) -> 0-1
            else:
                val = val / 2.0
            values.append(val)
        values_closed = values + [values[0]]

        ax.plot(angles_closed, values_closed, "o-", linewidth=2, label=model, color=colors[i], markersize=5)
        ax.fill(angles_closed, values_closed, alpha=0.15, color=colors[i])

    # Metric labels outside the outer ring
    for angle, metric in zip(angles, metrics):
        ax.text(angle, 1.08, metric, fontsize=12, fontweight="bold", ha="center", va="center")

    ax.set_ylim(0, 1)
    ax.set_rticks([])
    ax.set_xticks(angles)
    ax.set_xticklabels([])
    ax.grid(color="grey", linestyle="-", linewidth=0.5, alpha=0.3)

    ax.set_title("Quality Metrics Radar Chart\n(All metrics normalized to 0-1)", fontsize=14, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.08), fontsize=10)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Chart saved to: {output_path}")
    else:
        plt.show()

    plt.close(fig)
