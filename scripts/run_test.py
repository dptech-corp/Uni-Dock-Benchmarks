"""
Author: Congcong Liu
Brief: Benchmark Main Entry. Perform benchmark test for UD2 engine and UD1 engine on 
https://github.com/dptech-corp/Uni-Dock-Benchmarks
Usage: 
  * Molecular Docking:
    * for Uni-Dock (version 1), using the receptor with water
    python scripts/run_tests.py --version 1 --bin ud1 --type molecular_docking --device 1 --savedir res --seed 121
    * for Uni-Dock2 (version 2), using the receptor without water
    python scripts/run_tests.py --version 2 --bin ud2 --type molecular_docking --nowater --device 1 --savedir main_nowater_1 --seed 121
    
  * Virtual Screening:
    python scripts/run_tests.py --version 2 --bin ud2_v0.2 --type virtual_screening --device 0 --savedir res_vs --seed 122


Updated: 2025-06-05
"""
import os
import logging

from run_dock import run_benchmark_molecular_docking
from run_screen import run_benchmark_virtual_screening
from utils.config import BenchmarkConfig
from engines import create_engine

def run_benchmark_cli():
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--savedir", type=str, required=True, help="Saved directory for the results")
    parser.add_argument("--bin", type=str, required=True, help="Binary file of the docking tool")
    parser.add_argument("--version", type=int, choices=[1, 2], required=True, help="Version of the Uni-Dock engine binary, 1 or 2")
    parser.add_argument("--type", type=str, choices=["molecular_docking", "virtual_screening"], required=True, help="Type of the benchmark, molecular_docking or virtual_screening")
    parser.add_argument("--device", type=int, default=0, help="GPU device id, default is 0")
    parser.add_argument("--seed", type=int, default=123, help="Random seed")
    parser.add_argument("--nowater", action='store_true', help="Use receptor without water (default: uses water-containing receptor)")
    parser.add_argument("--rootdir", type=str, default=None, help=
                        "Root directory of the data, namely the 'Uni-Dock-Benchmarks' dir. If it's not provided, pls run under the 'Uni-Dock-Benchmarks' dir.")
    parser.add_argument("--dataset", type=str, default=None, help=
                        "Run only this dataset (e.g. 'Astex'). If not provided, run all datasets.")

    args = parser.parse_args()

    # savedir 是必须参数，先创建目录并配置logging
    os.makedirs(args.savedir, exist_ok=True)
    
    # 配置logging，同时输出到文件和控制台
    log_file = os.path.join(args.savedir, 'udbench.log')
    log_format = '[%(asctime)s][%(levelname)s]%(message)s'
    
    # 清除已有的handlers，避免重复
    logging.root.handlers = []
    
    # 配置logging
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # Find root directory
    if args.rootdir is None:
        # Try current directory first, then parent directory
        if os.path.exists(f"./data/{args.type}"):
            rootdir = Path(".").resolve()
        elif os.path.exists(f"../data/{args.type}"):
            rootdir = Path("..").resolve()
        else:
            logging.error(f"Could not find data directory. Please specify --rootdir or run from the correct location.")
            exit(-1)
    else:
        rootdir = Path(args.rootdir).resolve()
        fp = os.path.join(rootdir, "data", args.type)
        if not os.path.exists(fp):
            logging.error(f"rootdir: {fp} not found!")
            exit(-1)
    rootdir = str(rootdir)

    # Create configuration object from arguments
    benchmark_config = BenchmarkConfig(
        version=args.version,
        device_id=args.device,
        seed=args.seed,
        bin=args.bin,
        nowater=args.nowater,
        type=args.type,
        rootdir=rootdir,
        savedir=args.savedir
    )
    
    # 打印配置参数到日志
    config_str = benchmark_config.print_config()
    logging.info(f"\n{config_str}\n")
    
    # Create engine and run benchmark
    engine = create_engine(benchmark_config)

    if args.type == "molecular_docking":
        run_benchmark_molecular_docking(engine, datasets=[args.dataset] if args.dataset else None)
    else:  # virtual_screening
        run_benchmark_virtual_screening(engine)


if __name__ == "__main__":
    run_benchmark_cli()