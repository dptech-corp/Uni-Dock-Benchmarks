"""
Benchmark Main Entry.

Supports two usage modes:
  1. CLI:  python scripts/run_test.py --version 2 --bin ud2 --type molecular_docking ...
  2. Programmatic: import run_single() and call with a BenchmarkConfig

Examples (CLI):
  * Molecular Docking (Uni-Dock V1, receptor with water):
    python scripts/run_test.py --version 1 --bin ud1 --type molecular_docking --device 1 --savedir res --seed 121

  * Molecular Docking (Uni-Dock V2, receptor without water):
    python scripts/run_test.py --version 2 --bin ud2 --type molecular_docking --nowater --device 1 --savedir res --seed 121

  * Virtual Screening:
    python scripts/run_test.py --version 2 --bin ud2 --type virtual_screening --device 0 --savedir res_vs --seed 122
"""
import os
import logging
from pathlib import Path

from run_dock import run_benchmark_molecular_docking
from run_screen import run_benchmark_virtual_screening
from utils.config import BenchmarkConfig
from engines import create_engine


def setup_logging(savedir: str):
    """Configure logging with file and console handlers for a single run."""
    os.makedirs(savedir, exist_ok=True)
    log_file = os.path.join(savedir, 'udbench.log')
    log_format = '[%(asctime)s][%(levelname)s]%(message)s'
    logging.root.handlers = []
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def resolve_rootdir(rootdir_arg: str = None,
                    benchmark_type: str = "molecular_docking") -> str:
    """Resolve and validate the root directory of the benchmark data.

    Args:
        rootdir_arg: Explicit root directory path, or None for auto-detection.
        benchmark_type: Used to locate ``data/<type>`` for validation.

    Returns:
        Absolute path to the root directory.

    Raises:
        FileNotFoundError: If the data directory cannot be found.
    """
    if rootdir_arg is None:
        if os.path.exists(f"./data/{benchmark_type}"):
            return str(Path(".").resolve())
        if os.path.exists(f"../data/{benchmark_type}"):
            return str(Path("..").resolve())
        raise FileNotFoundError(
            "Could not find data directory. "
            "Please specify --rootdir or run from the correct location."
        )
    rootdir = str(Path(rootdir_arg).resolve())
    fp = os.path.join(rootdir, "data", benchmark_type)
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Data directory not found: {fp}")
    return rootdir


def run_single(config: BenchmarkConfig, datasets=None):
    """Execute a single benchmark run.

    This is the core entry point used by both the CLI and the YAML orchestrator
    (``run_bench.py``).

    Args:
        config: Fully populated BenchmarkConfig.
        datasets: Optional list of dataset names to run. None means all.
    """
    setup_logging(config.savedir)
    logging.info("\n%s\n", config.print_config())

    engine = create_engine(config)

    if config.type == "molecular_docking":
        run_benchmark_molecular_docking(engine, datasets=datasets)
    else:
        run_benchmark_virtual_screening(engine, datasets=datasets)


def run_benchmark_cli():
    import argparse
    parser = argparse.ArgumentParser(
        description="Uni-Dock Benchmark — single run entry point"
    )
    parser.add_argument("--savedir", type=str, required=True,
                        help="Saved directory for the results")
    parser.add_argument("--bin", type=str, required=True,
                        help="Binary file of the docking tool")
    parser.add_argument("--version", type=int, choices=[1, 2], required=True,
                        help="Version of the Uni-Dock engine binary, 1 or 2")
    parser.add_argument("--type", type=str, required=True,
                        choices=["molecular_docking", "virtual_screening"],
                        help="Type of the benchmark")
    parser.add_argument("--device", type=int, default=0,
                        help="GPU device id, default is 0")
    parser.add_argument("--seed", type=int, default=123,
                        help="Random seed")
    parser.add_argument("--nowater", action='store_true',
                        help="Use receptor without water (default: uses water-containing receptor)")
    parser.add_argument("--rootdir", type=str, default=None,
                        help="Root directory of the data, namely the 'Uni-Dock-Benchmarks' dir. "
                             "If not provided, auto-detected from CWD.")
    parser.add_argument("--dataset", type=str, default=None,
                        help="Run only this dataset (e.g. 'Astex'). If not provided, run all datasets.")
    args = parser.parse_args()

    try:
        rootdir = resolve_rootdir(args.rootdir, args.type)
    except FileNotFoundError as e:
        logging.error(str(e))
        exit(-1)

    config = BenchmarkConfig(
        version=args.version,
        device_id=args.device,
        seed=args.seed,
        bin=args.bin,
        nowater=args.nowater,
        type=args.type,
        rootdir=rootdir,
        savedir=args.savedir,
    )

    run_single(config, datasets=[args.dataset] if args.dataset else None)


if __name__ == "__main__":
    run_benchmark_cli()
