#!/usr/bin/env python3
"""
YAML-driven benchmark orchestrator.

Reads a benchmark configuration YAML file and schedules runs across GPUs.
  - Runs assigned to the SAME GPU execute SEQUENTIALLY (accurate timing).
  - Runs on DIFFERENT GPUs execute IN PARALLEL.

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
# Config loading & validation
# ---------------------------------------------------------------------------

def load_config(yaml_path: str) -> dict:
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def validate_config(cfg: dict) -> None:
    """Raise ValueError if required fields are missing or invalid."""
    for section in ("engine", "benchmark", "output", "runs"):
        if section not in cfg:
            raise ValueError(f"Missing required config section: '{section}'")

    engine = cfg["engine"]
    if "version" not in engine:
        raise ValueError("engine.version is required")
    if engine["version"] not in (1, 2):
        raise ValueError(f"engine.version must be 1 or 2, got {engine['version']}")

    benchmark = cfg["benchmark"]
    if "type" not in benchmark:
        raise ValueError("benchmark.type is required")
    valid_types = ("molecular_docking", "virtual_screening")
    if benchmark["type"] not in valid_types:
        raise ValueError(
            f"benchmark.type must be one of {valid_types}, got '{benchmark['type']}'"
        )

    if "savedir" not in cfg["output"]:
        raise ValueError("output.savedir is required")

    runs = cfg["runs"]
    if not isinstance(runs, list) or len(runs) == 0:
        raise ValueError("runs must be a non-empty list")
    for i, run in enumerate(runs):
        if "seed" not in run:
            raise ValueError(f"runs[{i}].seed is required")
        if "device" not in run:
            raise ValueError(f"runs[{i}].device is required")


# ---------------------------------------------------------------------------
# Scheduling helpers
# ---------------------------------------------------------------------------

def group_runs_by_device(runs: list) -> dict[int, list[tuple[int, dict]]]:
    """Group run entries by device id, preserving original index."""
    groups: dict[int, list] = defaultdict(list)
    for idx, run in enumerate(runs):
        groups[run["device"]].append((idx, run))
    return dict(groups)


def _run_device_group(yaml_cfg: dict, group_runs: list[tuple[int, dict]],
                      rootdir: str, base_savedir: str,
                      datasets: list[str] | None) -> None:
    """Execute all runs assigned to one GPU, sequentially."""
    for run_idx, run_entry in group_runs:
        savedir = os.path.join(base_savedir, f"run_{run_idx + 1}")
        config = BenchmarkConfig.from_yaml_run(
            yaml_cfg, run_entry, rootdir, savedir,
        )
        run_single(config, datasets=datasets)


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
    args = parser.parse_args()

    # --- Load & validate ---
    cfg = load_config(args.config)
    validate_config(cfg)

    benchmark_type = cfg["benchmark"]["type"]
    rootdir = resolve_rootdir(args.rootdir, benchmark_type)
    base_savedir = str(Path(cfg["output"]["savedir"]).resolve())
    datasets = cfg["benchmark"].get("datasets")

    # --- Prepare output directory ---
    os.makedirs(base_savedir, exist_ok=True)
    shutil.copy2(args.config, os.path.join(base_savedir, "benchmark.yaml"))

    # --- Orchestrator logging (console only, before workers take over) ---
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s][orchestrator] %(message)s",
    )
    logging.info("Config:    %s", args.config)
    logging.info("Root dir:  %s", rootdir)
    logging.info("Output:    %s", base_savedir)
    logging.info("Datasets:  %s", datasets or "(all)")

    device_groups = group_runs_by_device(cfg["runs"])
    logging.info(
        "Total runs: %d across %d device(s)",
        len(cfg["runs"]), len(device_groups),
    )
    for device, runs in sorted(device_groups.items()):
        desc = ", ".join(f"run_{i+1}(seed={r['seed']})" for i, r in runs)
        logging.info("  Device %d: %s", device, desc)

    # --- Launch one process per device group ---
    processes: list[tuple[int, Process]] = []
    for device, group_runs in sorted(device_groups.items()):
        p = Process(
            target=_run_device_group,
            args=(cfg, group_runs, rootdir, base_savedir, datasets),
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
        logging.error("Failed device groups: %s", failed)
        return 1

    logging.info("All benchmark runs completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
