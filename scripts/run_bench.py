#!/usr/bin/env python3
"""
YAML-driven benchmark orchestrator.

Reads a benchmark configuration YAML file and schedules runs across GPUs.

Supports two YAML formats:

1. **Multi-task** (recommended): top-level ``tasks`` list — each task has its
   own engine, benchmark, output, and runs sections.  Tasks execute
   **serially** (one after another).

2. **Legacy single-task**: top-level engine/benchmark/output/runs — treated
   as a single task automatically.

Usage:
    python scripts/run_bench.py benchmark.yaml [--rootdir DIR]

    # or via the wrapper:
    ./run.sh benchmark.yaml
"""
import argparse
import logging
import os
import shutil
import sys
from collections import defaultdict
from multiprocessing import Process
from pathlib import Path

import yaml

from run_test import resolve_rootdir, run_single
from utils.config import BenchmarkConfig


# ---------------------------------------------------------------------------
# Auto savedir
# ---------------------------------------------------------------------------

def _auto_savedir(engine_cfg: dict, benchmark_cfg: dict) -> str:
    """Generate ``results/<binary>_<dock|screen>_<water|nowater>``."""
    binary = engine_cfg.get("binary")
    if not binary:
        binary = "ud2" if engine_cfg.get("version", 2) == 2 else "ud1"
    binary_name = os.path.basename(binary)

    type_short = (
        "dock" if benchmark_cfg["type"] == "molecular_docking" else "screen"
    )
    water_label = (
        "nowater" if benchmark_cfg.get("nowater", False) else "water"
    )
    return f"results/{binary_name}_{type_short}_{water_label}"


def _ensure_savedir(task_cfg: dict) -> None:
    """Fill in ``output.savedir`` if it is missing (auto-generate)."""
    output = task_cfg.get("output")
    if output and output.get("savedir"):
        return
    savedir = _auto_savedir(task_cfg["engine"], task_cfg["benchmark"])
    if output is None:
        task_cfg["output"] = {"savedir": savedir}
    else:
        output["savedir"] = savedir


# ---------------------------------------------------------------------------
# Config loading, normalisation & validation
# ---------------------------------------------------------------------------

def load_config(yaml_path: str) -> dict:
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def normalize_config(raw_cfg: dict) -> list[dict]:
    """Convert a raw YAML config to a list of single-task config dicts.

    - If ``tasks`` key exists → multi-task format.
    - Otherwise → legacy single-task format (wrapped in a one-element list).
    """
    if "tasks" in raw_cfg:
        return list(raw_cfg["tasks"])
    return [raw_cfg]


def validate_task(task_cfg: dict, task_idx: int = 0) -> None:
    """Raise ``ValueError`` if required fields are missing or invalid."""
    tag = f"tasks[{task_idx}]"

    for section in ("engine", "benchmark", "runs"):
        if section not in task_cfg:
            raise ValueError(f"{tag}: missing required section '{section}'")

    engine = task_cfg["engine"]
    if "version" not in engine:
        raise ValueError(f"{tag}: engine.version is required")
    if engine["version"] not in (1, 2):
        raise ValueError(
            f"{tag}: engine.version must be 1 or 2, got {engine['version']}"
        )

    benchmark = task_cfg["benchmark"]
    if "type" not in benchmark:
        raise ValueError(f"{tag}: benchmark.type is required")
    valid_types = ("molecular_docking", "virtual_screening")
    if benchmark["type"] not in valid_types:
        raise ValueError(
            f"{tag}: benchmark.type must be one of {valid_types}, "
            f"got '{benchmark['type']}'"
        )

    if not task_cfg.get("output", {}).get("savedir"):
        raise ValueError(
            f"{tag}: output.savedir is missing and could not be auto-generated"
        )

    runs = task_cfg["runs"]
    if not isinstance(runs, list) or len(runs) == 0:
        raise ValueError(f"{tag}: runs must be a non-empty list")
    for i, run in enumerate(runs):
        if "seed" not in run:
            raise ValueError(f"{tag}: runs[{i}].seed is required")
        if "device" not in run:
            raise ValueError(f"{tag}: runs[{i}].device is required")


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------

def group_runs_by_device(runs: list) -> dict[int, list[tuple[int, dict]]]:
    """Group run entries by device id, preserving original index."""
    groups: dict[int, list] = defaultdict(list)
    for idx, run in enumerate(runs):
        groups[run["device"]].append((idx, run))
    return dict(groups)


def _run_device_group(task_cfg: dict, group_runs: list[tuple[int, dict]],
                      rootdir: str, base_savedir: str,
                      datasets: list[str] | None) -> None:
    """Execute all runs assigned to one GPU, sequentially."""
    for run_idx, run_entry in group_runs:
        savedir = os.path.join(base_savedir, f"run_{run_idx + 1}")
        config = BenchmarkConfig.from_yaml_run(
            task_cfg, run_entry, rootdir, savedir,
        )
        run_single(config, datasets=datasets)


# ---------------------------------------------------------------------------
# Per-task executor
# ---------------------------------------------------------------------------

def run_task(task_cfg: dict, rootdir_arg: str | None) -> None:
    """Execute one task: resolve paths, save per-task YAML, launch runs."""
    benchmark_type = task_cfg["benchmark"]["type"]
    rootdir = resolve_rootdir(rootdir_arg, benchmark_type)
    base_savedir = str(Path(task_cfg["output"]["savedir"]).resolve())
    datasets = task_cfg["benchmark"].get("datasets")

    os.makedirs(base_savedir, exist_ok=True)

    # Save a standalone single-task benchmark.yaml for reproducibility
    per_task_yaml = os.path.join(base_savedir, "benchmark.yaml")
    with open(per_task_yaml, "w") as f:
        yaml.dump(task_cfg, f, default_flow_style=False, sort_keys=False)

    logging.info("Config:    %s", per_task_yaml)
    logging.info("Root dir:  %s", rootdir)
    logging.info("Output:    %s", base_savedir)
    logging.info("Type:      %s", benchmark_type)
    logging.info("Datasets:  %s", datasets or "(all)")

    device_groups = group_runs_by_device(task_cfg["runs"])
    logging.info(
        "Total runs: %d across %d device(s)",
        len(task_cfg["runs"]), len(device_groups),
    )
    for device, runs in sorted(device_groups.items()):
        desc = ", ".join(f"run_{i+1}(seed={r['seed']})" for i, r in runs)
        logging.info("  Device %d: %s", device, desc)

    # --- Launch one process per device group ---
    processes: list[tuple[int, Process]] = []
    for device, group_runs in sorted(device_groups.items()):
        p = Process(
            target=_run_device_group,
            args=(task_cfg, group_runs, rootdir, base_savedir, datasets),
        )
        p.start()
        processes.append((device, p))
        logging.info("Launched device %d (PID %d)", device, p.pid)

    # --- Wait & report ---
    failed = []
    for device, p in processes:
        p.join()
        if p.exitcode != 0:
            failed.append(device)
            logging.error("Device %d FAILED (exit code %d)", device, p.exitcode)
        else:
            logging.info("Device %d completed", device)

    if failed:
        raise RuntimeError(f"Task failed on device(s): {failed}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="YAML-driven Uni-Dock benchmark orchestrator",
    )
    parser.add_argument("config", help="Path to benchmark YAML config file")
    parser.add_argument(
        "--rootdir", default=None,
        help="Root directory of benchmark data (default: auto-detect)",
    )
    parser.add_argument(
        "--print-savedir", action="store_true",
        help="Print the first task's savedir and exit (used by run.sh)",
    )
    args = parser.parse_args()

    # --- Load & normalise ---
    raw_cfg = load_config(args.config)
    tasks = normalize_config(raw_cfg)

    for task_cfg in tasks:
        _ensure_savedir(task_cfg)

    # --- Quick exit: just print savedir for the shell wrapper ---
    if args.print_savedir:
        print(tasks[0]["output"]["savedir"])
        return 0

    # --- Validate all tasks up-front ---
    for idx, task_cfg in enumerate(tasks):
        validate_task(task_cfg, idx)

    # --- Orchestrator logging ---
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][orchestrator] %(message)s",
    )
    logging.info("Loaded %d task(s) from %s", len(tasks), args.config)

    # --- Execute tasks serially ---
    for task_idx, task_cfg in enumerate(tasks):
        logging.info("=" * 60)
        logging.info(
            "TASK %d/%d: %s | %s | savedir=%s",
            task_idx + 1, len(tasks),
            task_cfg["benchmark"]["type"],
            "nowater" if task_cfg["benchmark"].get("nowater") else "water",
            task_cfg["output"]["savedir"],
        )
        logging.info("=" * 60)

        run_task(task_cfg, args.rootdir)
        logging.info("Task %d/%d completed.", task_idx + 1, len(tasks))

    logging.info("All %d task(s) completed successfully.", len(tasks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
