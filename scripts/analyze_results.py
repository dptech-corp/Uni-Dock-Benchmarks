#!/usr/bin/env python3
"""
Aggregate benchmark outputs from one or more run directories.

This script merges `metrics.csv`/`res.csv` from multiple runs and optionally
produces comparison plots (the same style as show_udbench.ipynb's
``plot_benchmark``).
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Uni-Dock benchmark results from multiple run directories."
    )
    parser.add_argument(
        "--runs",
        required=True,
        nargs="+",
        help="One or more parent directories containing run sub-directories (run_*). "
             "e.g. results/ud2_v055_dock/ results/ud2_v060_dock/",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="analysis",
        help="Output directory for merged tables and plots (default: analysis).",
    )
    parser.add_argument(
        "--name",
        nargs="+",
        default=["summary"],
        help="Legend labels for each --runs directory, and the first one is "
             "used as the output file prefix (default: summary).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["docking", "screening", "auto", "all"],
        default="auto",
        help="Benchmark mode: docking, screening, or auto-detect (default: auto).",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Disable plot generation and export tables only.",
    )
    parser.add_argument(
        "--no-date",
        action="store_true",
        help="Hide the date stamp in the plot title.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Discovery & table helpers
# ---------------------------------------------------------------------------

def discover_run_dirs(parent: str) -> list[Path]:
    """Find all run_* sub-directories under *parent*, sorted naturally."""
    parent_path = Path(parent).expanduser().resolve()
    if not parent_path.is_dir():
        logging.error("Parent directory does not exist: %s", parent_path)
        return []
    run_dirs = sorted(
        (d for d in parent_path.iterdir() if d.is_dir() and d.name.startswith("run_")),
        key=lambda d: d.name,
    )
    if not run_dirs:
        logging.warning("No run_* sub-directories found under %s", parent_path)
    else:
        logging.info("Found %d run(s) under %s: %s", len(run_dirs), parent_path,
                      ", ".join(d.name for d in run_dirs))
    return run_dirs


def read_table(fp: Path) -> pd.DataFrame | None:
    if not fp.exists():
        return None
    try:
        return pd.read_csv(fp)
    except Exception as exc:  # pragma: no cover
        logging.warning("Failed reading %s: %s", fp, exc)
        return None


def add_run_info(df: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "run_name", run_dir.name)
    out.insert(1, "run_dir", str(run_dir))
    return out


# ---------------------------------------------------------------------------
# Figure layout constants (adjust these for paper figures)
# ---------------------------------------------------------------------------
FIG_WIDTH = 13.0
FIG_HEIGHT = 4.0
FIG_DPI = 600
FONT_SIZES = {
    "title": 16,
    "label": 14,
    "tick": 14,
    "legend": 12,
    "bar_text": 12,
}

# ---------------------------------------------------------------------------
# Plotting helpers (ported from show_udbench.ipynb)
# ---------------------------------------------------------------------------

FONT: dict[str, int] = {}


def read_rounds(dp, keys: list | str, list_dataset: list | str):
    list_df = []
    for repeat in os.listdir(dp):
        fp_metrics = os.path.join(dp, repeat, "metrics.csv")
        if not os.path.exists(fp_metrics):
            continue
        df = pd.read_csv(fp_metrics)
        list_df.append(df)
    df = pd.concat(list_df)
    res = [list_dataset]
    for k in keys:
        res.append([np.mean(df[df["dataset"] == dataset][k].values) for dataset in list_dataset])
    return res


def plot_bar(
    list_data,
    xnames,
    list_label=None,
    xlabel=None,
    ylabel=None,
    text_perc=True,
    text_nf=None,
    ax=None,
    show_legend=True,
    y_hi=None,
):
    import matplotlib.pyplot as plt

    colors = [
        "#4C72B0", "#55A868", "#DD8452", "#C44E52", "#8172B3",
        "#937860", "#84B1CD", "#6A915D", "#D77FB4", "#7F7F7F",
    ]

    if ax is None:
        ax = plt.gca()

    n_method = len(list_data)
    n_dataset = len(xnames)

    if list_label is None:
        list_label = [None] * n_method

    group_width = 0.8
    bar_width = group_width / n_method
    list_x = np.arange(n_dataset)
    offset = (n_method - 1) / 2

    for i, data in enumerate(list_data):
        bars = ax.bar(
            list_x + (i - offset) * bar_width,
            data,
            bar_width,
            label=list_label[i],
            color=colors[i % len(colors)],
            alpha=0.9,
            linewidth=0.5,
        )

        for bar in bars:
            val = bar.get_height()
            if text_nf is not None:
                fmt = f"{{:.{int(text_nf)}f}}"
            else:
                fmt = "{:.1f}"

            if text_perc:
                text = fmt.format(val * 100) + "%"
            else:
                text = fmt.format(val)

            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val,
                text,
                ha="center",
                va="bottom",
                fontsize=FONT["bar_text"],
            )

    ax.set_xticks(list_x)
    ax.set_xticklabels(xnames, fontsize=FONT["tick"])
    ax.tick_params(axis="y", labelsize=FONT["tick"])

    if xlabel:
        ax.set_xlabel(xlabel, fontsize=FONT["label"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=FONT["label"])

    if show_legend and any(list_label):
        ax.legend(fontsize=FONT["legend"], frameon=False, loc="best")

    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    y_ticks = ax.get_yticks()
    if len(y_ticks) > 0:
        y_max_tick = y_ticks[-1]
        y_min = ax.get_ylim()[0]
        ax.set_ylim(bottom=y_min, top=y_max_tick)
    if y_hi is not None:
        ax.set_ylim(top=y_hi)


def plot_bar_hit_rates(list_data, xlabels, list_label=None, ax=None, show_legend=True):
    list_data_pct = [[v * 100 for v in vals] for vals in list_data]
    plot_bar(
        list_data_pct, xlabels, list_label,
        xlabel="Dataset",
        ylabel="Success Rate (%)",
        text_perc=False,
        text_nf=0,
        ax=ax,
        show_legend=show_legend,
        y_hi=100,
    )


def plot_bar_cost(list_data, xlabels, list_label=None, ax=None, show_legend=True):
    plot_bar(
        list_data, xlabels, list_label,
        xlabel="Dataset",
        ylabel="Time Cost per Ligand (s)",
        text_perc=False,
        ax=ax,
        show_legend=show_legend,
    )


def plot_benchmark(
    result_dirs,
    xlabels=None,
    data_keys=None,
    prefixes=None,
    mode="docking",
    figfile=None,
    show_date=True,
):
    """
    Unified benchmark plotting for docking or screening.

    Features:
    - Adaptive subplots
    - Adaptive figure size and fonts
    - Optional water detection for docking
    - Legend placed outside last subplot
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    global FONT

    if mode == "docking":
        if xlabels is None:
            xlabels = ["Astex", "CASF2016", "PoseBuster"]
        if data_keys is None:
            data_keys = ["hit_rate_rmsd2.0", "avr_time(s)"]
        ylabel_list = ["Hit Rate (RMSD < 2.0)", "Average Time Cost (s)"]
        text_perc = [True, False]
        text_nf = [0, None]
        title_prefix = "Benchmark Result of Molecular Docking"

    elif mode == "screening":
        if xlabels is None:
            xlabels = ["D4", "NSP3", "PPARG", "sigma2"]
        if data_keys is None:
            data_keys = ["Enrichment (5%)", "Cost (s/ligand)"]
        ylabel_list = ["Enrichment Factor (5%)", "Time Cost per Ligand (s)"]
        text_perc = [False, False]
        text_nf = [2, 2]
        title_prefix = "Benchmark Result of Virtual Screening"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    n_subplots = len(data_keys)
    data_list = [[] for _ in range(n_subplots)]
    labels = []

    for i, dp in enumerate(result_dirs):
        res = read_rounds(dp, data_keys, xlabels)
        for j in range(n_subplots):
            data_list[j].append(res[j + 1])

        basename = os.path.basename(dp)

        if prefixes is not None:
            labels.append(prefixes[i])
        else:
            version = basename.split("_")[1] if "_" in basename else basename
            if basename.startswith("res1"):
                prefix = "ud1"
            elif basename.startswith("res2"):
                prefix = "ud2"
            else:
                prefix = basename
            labels.append(f"{prefix}_{version}")

    FONT = dict(FONT_SIZES)
    fig = plt.figure(figsize=(FIG_WIDTH, FIG_HEIGHT), dpi=FIG_DPI)

    gs = fig.add_gridspec(1, n_subplots, wspace=0.25)
    axes = [fig.add_subplot(gs[0, i]) for i in range(n_subplots)]

    import math

    for i in range(n_subplots):
        data_max = max(max(vals) for vals in data_list[i])
        if mode == "docking":
            if i == 0:
                plot_bar_hit_rates(data_list[i], xlabels, labels, ax=axes[i], show_legend=False)
            else:
                plot_bar_cost(data_list[i], xlabels, labels, ax=axes[i], show_legend=False)
                y_max = math.ceil(data_max) + 1
                axes[i].set_ylim(top=y_max)
                axes[i].yaxis.set_major_locator(plt.MultipleLocator(1))
        else:
            plot_bar(
                data_list[i],
                xlabels,
                list_label=labels,
                ax=axes[i],
                xlabel="Dataset",
                ylabel=ylabel_list[i],
                text_perc=text_perc[i],
                text_nf=text_nf[i],
                show_legend=False,
            )
            if i == 0:
                y_max = math.ceil(data_max) + 1
                axes[i].set_ylim(top=y_max)
                axes[i].yaxis.set_major_locator(plt.MultipleLocator(1))
            if i == n_subplots - 1:
                y_max = math.ceil(data_max / 0.05) * 0.05
                axes[i].set_ylim(top=y_max)
                axes[i].yaxis.set_major_locator(plt.MultipleLocator(0.05))

    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        loc="center left",
        bbox_to_anchor=(0.9, 0.5),
        fontsize=FONT["legend"],
        frameon=False,
    )

    str_water = ""
    if mode == "docking":
        last_dir = result_dirs[-1] if isinstance(result_dirs[-1], str) else result_dirs[-1][0]
        try:
            import yaml as _yaml
            fp_yaml = os.path.join(last_dir, "benchmark.yaml")
            if os.path.exists(fp_yaml):
                with open(fp_yaml, "r") as f:
                    cfg = _yaml.safe_load(f)
                nowater = cfg.get("benchmark", {}).get("nowater", False)
                str_water = "Without Water" if nowater else "With Water"
            elif "nowater" in os.path.basename(last_dir):
                str_water = "Without Water"
            else:
                str_water = "With Water"
        except Exception as e:
            logging.warning("Could not detect water status: %s", e)
            if "nowater" in os.path.basename(last_dir):
                str_water = "Without Water"
            else:
                str_water = "With Water"

    title = title_prefix
    if str_water:
        title += f" ({str_water})"
    if show_date:
        title += f"\nUpdate: {time.strftime('%Y-%m-%d', time.localtime())}"
    fig.suptitle(title, fontsize=FONT["title"], y=1)

    if figfile is not None:
        fig.savefig(figfile, dpi=FIG_DPI, bbox_inches="tight")
        logging.info("Saved plot: %s", figfile)
    plt.tight_layout()
    plt.close(fig)
    return fig


def plot_combined_benchmark(
    dock_water_dirs,
    dock_nowater_dirs,
    screen_dirs,
    labels,
    figfile=None,
    show_date=True,
):
    """Generate a single figure with 3 rows: dock water, dock nowater, screening."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import math

    global FONT
    FONT = dict(FONT_SIZES)

    dock_xlabels = ["Astex", "CASF2016", "PoseBuster"]
    dock_keys = ["hit_rate_rmsd2.0", "avr_time(s)"]
    screen_xlabels = ["D4", "NSP3", "PPARG", "sigma2"]
    screen_keys = ["Enrichment (5%)", "Cost (s/ligand)"]

    rows_config = [
        ("Molecular Docking With Water", "docking", dock_water_dirs, dock_xlabels, dock_keys),
        ("Molecular Docking Without Water", "docking", dock_nowater_dirs, dock_xlabels, dock_keys),
        ("Virtual Screening", "screening", screen_dirs, screen_xlabels, screen_keys),
    ]

    fig = plt.figure(figsize=(FIG_WIDTH, FIG_HEIGHT * 3), dpi=FIG_DPI)
    subfigs = fig.subfigures(3, 1, hspace=0.06)

    legend_ax = None

    for row_idx, (title, mode, result_dirs, xlabels, data_keys) in enumerate(rows_config):
        sf = subfigs[row_idx]
        axes = sf.subplots(1, 2)
        sf.subplots_adjust(wspace=0.25)
        sf.suptitle(title, fontsize=FONT["title"])

        data_list = [[], []]
        for dp in result_dirs:
            res = read_rounds(dp, data_keys, xlabels)
            for j in range(2):
                data_list[j].append(res[j + 1])

        if mode == "docking":
            plot_bar_hit_rates(data_list[0], xlabels, labels, ax=axes[0], show_legend=False)
            plot_bar_cost(data_list[1], xlabels, labels, ax=axes[1], show_legend=False)
            data_max = max(max(vals) for vals in data_list[1])
            y_max = math.ceil(data_max) + 1
            axes[1].set_ylim(top=y_max)
            axes[1].yaxis.set_major_locator(plt.MultipleLocator(1))
        else:
            plot_bar(data_list[0], xlabels, list_label=labels, ax=axes[0],
                     xlabel="Dataset", ylabel="Enrichment Factor",
                     text_perc=False, text_nf=2, show_legend=False)
            data_max_e = max(max(vals) for vals in data_list[0])
            y_max = math.ceil(data_max_e) + 1
            axes[0].set_ylim(top=y_max)
            axes[0].yaxis.set_major_locator(plt.MultipleLocator(1))

            plot_bar(data_list[1], xlabels, list_label=labels, ax=axes[1],
                     xlabel="Dataset", ylabel="Time Cost per Ligand (s)",
                     text_perc=False, text_nf=2, show_legend=False)
            data_max_c = max(max(vals) for vals in data_list[1])
            y_max = math.ceil(data_max_c / 0.05) * 0.05
            axes[1].set_ylim(top=y_max)
            axes[1].yaxis.set_major_locator(plt.MultipleLocator(0.05))

        panel_label = chr(ord("A") + row_idx)
        axes[0].text(-0.15, 1.05, f"({panel_label})", transform=axes[0].transAxes,
                     fontsize=FONT["title"], fontweight="bold", va="bottom", ha="left")

        if row_idx == 0:
            legend_ax = axes[1]

    legend_ax.legend(fontsize=FONT["legend"], frameon=False, loc="upper right")

    if show_date:
        fig.text(0.5, 1.0, f"Update: {time.strftime('%Y-%m-%d', time.localtime())}",
                 ha="center", fontsize=FONT["title"])

    if figfile is not None:
        fig.savefig(figfile, dpi=FIG_DPI, bbox_inches="tight")
        logging.info("Saved combined plot: %s", figfile)
    plt.close(fig)
    return fig


def detect_mode(metrics_df: pd.DataFrame) -> str:
    """Auto-detect benchmark mode from column names."""
    if "hit_rate_rmsd2.0" in metrics_df.columns:
        return "docking"
    if "Enrichment (5%)" in metrics_df.columns or "Enrichment (1%)" in metrics_df.columns:
        return "screening"
    return "docking"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = parse_args()
    if pd is None:
        logging.error("pandas is required. Please run: pip install pandas")
        return 1

    prefixes: list[str] = list(args.name)
    legend_labels = prefixes[1:] if len(prefixes) > 1 else prefixes
    file_prefix = prefixes[0]

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # --mode all: combined 3-row figure (dock water, dock nowater, screening)
    # --runs order: dock_water dirs, dock_nowater dirs, screen dirs
    if args.mode == "all":
        if np is None:
            logging.error("numpy is required for plotting.")
            return 1
        n_methods = len(legend_labels)
        expected = 3 * n_methods
        if len(args.runs) != expected:
            logging.error("--mode all requires %d --runs dirs "
                          "(3 scenarios x %d methods), got %d",
                          expected, n_methods, len(args.runs))
            return 1
        runs_paths = [str(Path(r).expanduser().resolve()) for r in args.runs]
        dock_water_dirs = runs_paths[0:n_methods]
        dock_nowater_dirs = runs_paths[n_methods:2 * n_methods]
        screen_dirs = runs_paths[2 * n_methods:3 * n_methods]

        figfile = str(output_dir / f"{file_prefix}_benchmark.png")
        plot_combined_benchmark(
            dock_water_dirs=dock_water_dirs,
            dock_nowater_dirs=dock_nowater_dirs,
            screen_dirs=screen_dirs,
            labels=legend_labels,
            figfile=figfile,
            show_date=not args.no_date,
        )
        logging.info("Analysis complete. Output directory: %s", output_dir)
        return 0

    # Single-mode flow: docking / screening / auto
    runs_paths: list[str] = []
    if len(prefixes) < len(args.runs):
        prefixes.extend(prefixes[-1:] * (len(args.runs) - len(prefixes)))

    metrics_list: list[pd.DataFrame] = []
    for idx, parent in enumerate(args.runs):
        run_dirs = discover_run_dirs(parent)
        if not run_dirs:
            logging.error("No valid run directory found under %s", parent)
            return 1
        runs_paths.append(str(Path(parent).expanduser().resolve()))

        for run_dir in run_dirs:
            fp_metrics = run_dir / "metrics.csv"
            df_metrics = read_table(fp_metrics)
            if df_metrics is not None and not df_metrics.empty:
                metrics_list.append(add_run_info(df_metrics, run_dir))
            else:
                logging.warning("metrics.csv missing or empty in %s", run_dir)

    if not metrics_list:
        logging.error("No valid metrics.csv found from the provided runs.")
        return 1

    df_metrics_all = pd.concat(metrics_list, ignore_index=True)
    fp = output_dir / f"{file_prefix}_metrics_merged.csv"
    df_metrics_all.to_csv(fp, index=False)
    logging.info("Saved merged metrics: %s", fp)

    if not args.no_plot:
        if np is None:
            logging.error("numpy is required for plotting. Please run: pip install numpy")
            return 1
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            logging.info("matplotlib is unavailable; skip plot generation.")
            return 0

        mode = args.mode
        if mode == "auto":
            mode = detect_mode(df_metrics_all)
            logging.info("Auto-detected mode: %s", mode)

        figfile = str(output_dir / f"{file_prefix}_benchmark.png")
        plot_benchmark(
            result_dirs=runs_paths,
            prefixes=legend_labels,
            mode=mode,
            figfile=figfile,
            show_date=not args.no_date,
        )

    logging.info("Analysis complete. Output directory: %s", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
