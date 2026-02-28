"""
Common utilities shared between run_dock.py and run_screen.py
"""
import os
import time
import subprocess as sp
import yaml
import logging
from typing import Dict, Optional

from utils.config import BenchmarkConfig
from utils.myio import write_yaml


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


def load_ud2_config(script_dir: Optional[str] = None) -> dict:
    """
    Load the default ud2.yaml configuration file.
    
    Args:
        script_dir: Directory containing ud2.yaml. If None, uses current script directory.
    
    Returns:
        Dictionary containing the YAML configuration
    """
    if script_dir is None:
        script_dir = os.path.dirname(os.path.dirname(__file__))
    
    fp_ud2_yaml = os.path.join(script_dir, "ud2.yaml")
    with open(fp_ud2_yaml, "r") as f:
        config_ud2 = yaml.safe_load(f)
    
    # Return a deep copy to avoid modifying the original
    import copy
    return copy.deepcopy(config_ud2)


def gen_cmd_ud2(
    fp_json: str,
    data_center: Dict[str, float],
    dp_res_case: str,
    search_mode: str,
    config: BenchmarkConfig,
    use_log: bool = True,
    center_format: str = "molecular_docking"
) -> list:
    """
    Generate command for Uni-Dock V2.
    
    Args:
        fp_json: Path to input JSON file
        data_center: Dictionary containing center coordinates and box sizes
        dp_res_case: Output directory for results
        search_mode: Search mode (e.g., "free", "fast", "detail")
        config: BenchmarkConfig object
        use_log: Whether to use --log flag (molecular_docking uses it, virtual_screening doesn't)
        center_format: "molecular_docking" uses 'X'/'Y'/'Z' with fixed size 30.0,
                      "virtual_screening" uses 'center_x'/'center_y'/'center_z' with variable sizes
    
    Returns:
        Command list for subprocess
    """
    # Load default config
    config_ud2 = load_ud2_config()
    
    # Set configuration values
    config_ud2["Advanced"]["seed"] = config.seed
    config_ud2["Settings"]["search_mode"] = search_mode
    
    # Set center coordinates and box sizes based on format
    if center_format == "molecular_docking":
        config_ud2["Settings"]["center_x"] = data_center['X']
        config_ud2["Settings"]["center_y"] = data_center['Y']
        config_ud2["Settings"]["center_z"] = data_center['Z']
        config_ud2["Settings"]["size_x"] = 30.0
        config_ud2["Settings"]["size_y"] = 30.0
        config_ud2["Settings"]["size_z"] = 30.0
    else:  # virtual_screening
        config_ud2["Settings"]["center_x"] = data_center['center_x']
        config_ud2["Settings"]["center_y"] = data_center['center_y']
        config_ud2["Settings"]["center_z"] = data_center['center_z']
        config_ud2["Settings"]["size_x"] = data_center['size_x']
        config_ud2["Settings"]["size_y"] = data_center['size_y']
        config_ud2["Settings"]["size_z"] = data_center['size_z']
    
    config_ud2["Inputs"]["json"] = fp_json
    config_ud2["Outputs"]["dir"] = dp_res_case
    config_ud2["Hardware"]["gpu_device_id"] = config.device_id
    
    # Write config file
    fp_ud2_config = os.path.join(dp_res_case, "ud2.yaml")
    write_yaml(config_ud2, fp_ud2_config)
    
    # Generate command
    if use_log:
        cmd = [config.binary, "--log", os.path.join(dp_res_case, "ud2.log"), fp_ud2_config]
    else:
        cmd = [config.binary, fp_ud2_config]
    
    return cmd


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

