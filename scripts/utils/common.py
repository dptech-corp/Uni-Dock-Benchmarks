"""
Common utilities shared between run_dock.py and run_screen.py
"""
import os
import time
import subprocess as sp
import logging

from utils.config import BenchmarkConfig


def prepare_dirs(config: BenchmarkConfig) -> tuple:
    """
    Prepare data and result directories.
    
    Args:
        config: BenchmarkConfig object containing 'rootdir', 'type', and 'savedir'
    
    Returns:
        Tuple of (dp_data, dp_res)
    """
    dp_root = config.rootdir
    dp_data = os.path.join(dp_root, "data", config.type)
    dp_res = config.savedir
    os.makedirs(dp_res, exist_ok=True)
    return dp_data, dp_res


def run_command(cmd: list, capture_output: bool = True) -> tuple:
    """
    Run a command and return the result.
    
    Args:
        cmd: Command list for subprocess
        capture_output: Whether to capture stdout/stderr
    
    Returns:
        Tuple of (returncode, cost_time, stdout, stderr)
    """
    start_time = time.time()
    status = sp.run(cmd, encoding="utf-8", capture_output=capture_output)
    end_time = time.time()
    cost_time = end_time - start_time
    
    if status.returncode != 0:
        if capture_output:
            logging.info(status.stdout)
            logging.error(status.stderr)
    
    return status.returncode, cost_time, status.stdout if capture_output else "", status.stderr if capture_output else ""


def check_rerun(fp_result: str, rerun: bool) -> bool:
    """
    Check if result file exists and handle rerun logic.
    
    Args:
        fp_result: Path to result file
        rerun: Whether to rerun if file exists
    
    Returns:
        True if should continue (skip existing or rerun), False if should skip
    """
    if os.path.exists(fp_result):
        logging.warning(f"{fp_result} already exists!")
        if not rerun:
            return False  # Skip
        else:
            logging.warning(f"*RERUN* Overwriting existing results file: {fp_result}")
            return True  # Continue with rerun
    return True  # Continue (file doesn't exist)
