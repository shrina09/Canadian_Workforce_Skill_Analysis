# Visualizes the STEM vs BHASE skill comparison data with bar charts and heatmaps
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError as exc: 
    raise SystemExit(
        "matplotlib is required for visualization. Install it with "
        "`pip install matplotlib` or `poetry add matplotlib`."
    ) from exc


CLEANED_DIR = Path.home() / "Documents" / "CIS4900" / "Cleaned"
DEFAULT_INPUT = CLEANED_DIR / "skills_group_comparison.csv"
DEFAULT_OUTPUT_DIR = CLEANED_DIR / "visualizations"


# Builds CLI arguments so this script can be run with custom input/output settings
def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate STEM vs BHASE skill comparison visualizations."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to the combined comparison CSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save output images. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=15,
        help="Number of skills to show in each visualization. Default: 15",
    )
    return parser


# Loads and validate the combined STEM/BHASE comparison table
def load_comparison_data(path):
    if not path.exists():
        raise FileNotFoundError(f"Comparison CSV not found: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "skill",
        "stem_count",
        "bhase_count",
        "stem_freq",
        "bhase_freq",
        "freq_diff_stem_minus_bhase",
    }
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")

    numeric_columns = [
        "stem_count",
        "bhase_count",
        "stem_freq",
        "bhase_freq",
        "freq_diff_stem_minus_bhase",
    ]
    for column in numeric_columns:
       # Converts values to numbers, if it fails, replace with 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    # Total count is used to rank top skills for multiple plots.
    df["total_count"] = df["stem_count"] + df["bhase_count"]
    return df


#plots bar chart
def plot_top_skills_by_group(df, output_dir, top_n):
    # Side-by-side bar chart of top skills by total appearance count
    top_df = df.nlargest(top_n, "total_count").sort_values("total_count", ascending=True)

    # Re-sort for left-to-right display from highest to lowest
    top_df = top_df.sort_values("total_count", ascending=False).reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(16, 8))
    x_positions = range(len(top_df))
    bar_width = 0.38

    ax.bar(
        [x - bar_width / 2 for x in x_positions],
        top_df["stem_count"],
        width=bar_width,
        label="STEM",
        color="#2e8b57",
        alpha=0.9,
    )
    ax.bar(
        [x + bar_width / 2 for x in x_positions],
        top_df["bhase_count"],
        width=bar_width,
        label="BHASE",
        color="#e8a317",
        alpha=0.9,
    )

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(top_df["skill"], rotation=45, ha="right")
    ax.set_ylabel("Count")
    ax.set_title(f"Top {top_n} Skills by Total Count", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    output_path = output_dir / "top_skills_by_group.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


#plots Horizontal frequency bar chart
def plot_skill_frequency_difference(df, output_dir, top_n):
    # Horizontal bar chart showing which group each skill is relatively more common in
    diff_df = (
        df.assign(abs_diff=df["freq_diff_stem_minus_bhase"].abs())
        .nlargest(top_n, "abs_diff")
        .sort_values("freq_diff_stem_minus_bhase")
    )

    # Green means STEM-leaning, orange means BHASE-leaning
    colors = [
        "#2e8b57" if value >= 0 else "#e8a317"
        for value in diff_df["freq_diff_stem_minus_bhase"]
    ]

    fig, ax = plt.subplots(figsize=(12, 8))
    diff_percent = diff_df["freq_diff_stem_minus_bhase"] * 100
    ax.barh(diff_df["skill"], diff_percent, color=colors, alpha=0.9)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Difference in Frequency Percentage Points (BHASE < 0 | STEM > 0)")
    ax.set_title(f"Top {top_n} Skills by Frequency Difference", fontweight="bold")
    ax.grid(axis="x", linestyle="--", alpha=0.3)
    ax.text(
        0.02,
        1.02,
        "More common in BHASE",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        color="#e8a317",
        fontsize=10,
        fontweight="bold",
    )
    ax.text(
        0.98,
        1.02,
        "More common in STEM",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color="#2e8b57",
        fontsize=10,
        fontweight="bold",
    )

    output_path = output_dir / "skill_frequency_difference.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


#plots heatmap
def plot_skill_heatmap(df, output_dir, top_n):
    # Heatmap comparing STEM and BHASE frequencies for top total-count skills
    heatmap_df = (
        df.nlargest(top_n, "total_count")[["skill", "stem_freq", "bhase_freq"]]
        .set_index("skill")
        .sort_values("stem_freq", ascending=False)
    )

    # Scale height with number of rows so labels stay readable
    fig_height = max(6, top_n * 0.45)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    image = ax.imshow(heatmap_df[["stem_freq", "bhase_freq"]].values, cmap="YlOrBr", aspect="auto")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["STEM", "BHASE"])
    ax.set_yticks(range(len(heatmap_df.index)))
    ax.set_yticklabels(heatmap_df.index)
    ax.set_title(f"Heatmap of Top {top_n} Skills", fontweight="bold")

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Frequency")

    output_path = output_dir / "skills_heatmap.png"
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_path


# Runs the full visualization pipeline and print saved file locations
def main():
    args = build_parser().parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_comparison_data(args.input)

    top_skills_path = plot_top_skills_by_group(df, output_dir, args.top_n)
    diff_path = plot_skill_frequency_difference(df, output_dir, args.top_n)
    heatmap_path = plot_skill_heatmap(df, output_dir, args.top_n)
    scatter_path = plot_stem_vs_bhase_scatter(df, output_dir, args.top_n)

    print("Saved visualizations:")
    print(top_skills_path)
    print(diff_path)
    print(heatmap_path)
    print(scatter_path)


if __name__ == "__main__":
    main()
