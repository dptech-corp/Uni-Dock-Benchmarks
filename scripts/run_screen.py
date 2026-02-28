"""
Author: Congcong Liu
Brief: 
task: virtual screening
https://github.com/dptech-corp/Uni-Dock-Benchmarks

Updated: 2025-06-05
"""

import os
import traceback
from tqdm import tqdm
import pandas as pd
import logging

from utils.myio import read_text, write_text, read_json
from utils.config import BenchmarkConfig, FMT_UD1, FMT_UD2, CSV_NAME
from utils.common import prepare_dirs, gen_cmd_ud2, run_command, check_rerun

#------------------------ Uni-Dock V1 ------------------------    

def gen_cmd_ud1(fp_index, fp_receptor, data_center, dp_res_case, search_mode, config: BenchmarkConfig, rand=False):
    """Generate command for Uni-Dock V1 (virtual screening)."""
    base_cmd = [
        config.binary,
        "--receptor", str(fp_receptor),
        "--ligand_index", str(fp_index),
        "--center_x", f"{data_center['center_x']:.1f}",
        "--center_y", f"{data_center['center_y']:.1f}",
        "--center_z", f"{data_center['center_z']:.1f}",
        "--size_x", f"{data_center['size_x']:.1f}",
        "--size_y", f"{data_center['size_y']:.1f}",
        "--size_z", f"{data_center['size_z']:.1f}",
        "--dir", str(dp_res_case),
        "--keep_nonpolar_H",
        "--scoring", "vina",
        "--num_modes", "10",
        "--refine_step", "5",
        "--device_id", str(config.device_id),
        "--cpu", "32",
    ]
        
    if rand:
        cmd = base_cmd + [
            "--exhaustiveness", "512",
            "--num_modes", "512",
            "--min_rmsd", "-1", 
            "--energy_range", "9999999999", 
            "--max_step", "0", 
            "--refine_step", "0",
        ]
    else:
        cmd = base_cmd + ["--search_mode", search_mode]

    # print("cmd: ", " ".join(cmd))
    # return None
    return cmd


#------------------------ Main ------------------------    
def gen_cmd(dp_data, dataset, data_center, dp_res_case, search_mode, config: BenchmarkConfig):
    """Generate command for virtual screening."""
    cmd = []

    if config.version == 1:
        fp_pdb = os.path.join(dp_data, FMT_UD1[dataset]["pdb"])
        for name in ["inactive", "active"]:
            fp_sdf = os.path.join(dp_data, FMT_UD1[dataset][name])
            dp = os.path.join(dp_res_case, name)
            os.makedirs(dp, exist_ok=True)

            dp_split = os.path.join(dp, "split")
            os.makedirs(dp_split, exist_ok=True)
            fp_index = os.path.join(dp, "index.txt")

            ss_index = ""
            ss_sdf = read_text(fp_sdf).strip().strip("\n").rstrip("$$$$")
            for ss in ss_sdf.split("$$$$"):
                lig_name = ss.strip().strip("\n").split("\n")[0]
                fp_lig = os.path.join(dp_split, f"{lig_name}.sdf")
                write_text(ss.strip().strip("\n") + "\n\n$$$$", fp_lig)
                ss_index += fp_lig + " "
            write_text(ss_index, fp_index)

            cmd.append(gen_cmd_ud1(fp_index, fp_pdb, data_center, dp, search_mode, config))

    elif config.version == 2:
        for name in ["inactive", "active"]:
            fp_json = os.path.join(dp_data, FMT_UD2[dataset][name])
            dp = os.path.join(dp_res_case, name)
            os.makedirs(dp, exist_ok=True)
            cmd.append(gen_cmd_ud2(fp_json, data_center, dp, search_mode, config, use_log=False, center_format="virtual_screening"))

    return cmd

def get_affinity(dp_res_case, config: BenchmarkConfig):
    """Extract affinity scores from results."""
    res = []
    for active, name in enumerate(["inactive", "active"]):
        dp = os.path.join(dp_res_case, name)
        if config.version == 1:
            for fn in [i for i in os.listdir(dp) if i.endswith(".sdf")]:
                fp_sdf = os.path.join(dp, fn)
                ss = read_text(fp_sdf)
                ligand_name = fn.strip()[:-8]
                energy = float(ss.strip().split("$$$$")[0].split("ENERGY=")[-1].split("LOWER_BOUND=")[0].strip())
                res.append([ligand_name, energy, active])
        else:
            for fn in [i for i in os.listdir(dp) if i.endswith(".json")]:
                fp_json = os.path.join(dp, fn)
                data = read_json(fp_json)
                for ligand_name, poses in data.items():
                    res.append([ligand_name, poses[0]["energy"][0], active])

    fp_res = os.path.join(dp_res_case, CSV_NAME)
    df = pd.DataFrame(res, columns=["Ligand", "Affinity", "Active"])
    df.to_csv(fp_res, index=False)
    return df



def analysis_metrics(dp_res: str):
    """
    For given dp_res, calculate the metrics of all datasets and modes
    """
    fp_res = os.path.join(dp_res, CSV_NAME)
    df_res = pd.read_csv(fp_res)

    fp_metrics = os.path.join(dp_res, "metrics.csv")
    list_k = [0.5, 1, 5]
    columns = ["dataset", "Mode", "Cost (s/ligand)", "N_total", "N_active", "N_inactive"]
    for k in list_k:
        columns.extend([f"Hit ({k}%)", f"Enrichment ({k}%)"])

    list_data_metrics = []
    for dataset in df_res["dataset"].unique():
        df_dataset = df_res[df_res["dataset"] == dataset]         
        N_total = len(df_dataset)
        N_active = len(df_dataset[df_dataset["Active"] == 1])
        df_dataset.sort_values(by='Affinity', ascending=True, inplace=True) 
        avr_time = float(df_dataset.iloc[0]["cost_time"])
        mode = str(df_dataset.iloc[0]["mode"])
        line = [dataset, mode, avr_time, N_total, N_active, N_total - N_active]
        for k in list_k: # each K%
            k = k / 100
            N_sample = int(k * N_total)
            df_sample = df_dataset.head(N_sample)
            N_active_sample = len(df_sample[df_sample["Active"] == 1])
            EF = N_active_sample  / (N_active * k)
            line.extend([N_active_sample, EF])
        list_data_metrics.append(line)

    df_metrics = pd.DataFrame(list_data_metrics, columns=columns)
    df_metrics.to_csv(fp_metrics, index=False, float_format='%.3f')


def run_benchmark_virtual_screening(config: BenchmarkConfig, rerun: bool = True):
    """
    Run virtual screening benchmark.
    
    Args:
        config: BenchmarkConfig object containing all benchmark settings
        rerun: Whether to rerun if results already exist
    """
    dp_data, dp_res = prepare_dirs(config)
    search_mode_list = config.search_mode_list

    # Start Benchmark Test
    fp_res_all = os.path.join(dp_res, CSV_NAME)
    df_res_all = []

    # For each dataset
    for dataset in sorted(os.listdir(dp_data)):
        dp_data_dataset = os.path.join(dp_data, dataset)
    
        dp_res_dataset = os.path.join(dp_res, dataset)
        os.makedirs(dp_res_dataset, exist_ok=True)
        fp_res_dataset = os.path.join(dp_res_dataset, CSV_NAME)
        df_res_dataset = []
        # For each search mode
        for search_mode in search_mode_list:
            dp_res_mode = os.path.join(dp_res_dataset, search_mode)
            os.makedirs(dp_res_mode, exist_ok=True)
            fp_res_mode = os.path.join(dp_res_mode, CSV_NAME)
            
            if not check_rerun(fp_res_mode, rerun):
                # Load existing results if not rerunning
                if os.path.exists(fp_res_mode):
                    df_res_mode = pd.read_csv(fp_res_mode)
                    df_res_dataset.append(df_res_mode)
                continue

            df_res_mode = None
            try:
                # Start the test on this case
                dp_res_case = os.path.join(dp_res_mode, "tmp")
                os.makedirs(dp_res_case, exist_ok=True)
                fp_center = os.path.join(dp_data_dataset, "docking_grid.json")
                data_center = read_json(fp_center)

                # command
                list_cmd = gen_cmd(dp_data_dataset, dataset, data_center, dp_res_case, search_mode, config)
                # run
                total_cost = 0.0
                for cmd in list_cmd:
                    returncode, cost, stdout, stderr = run_command(cmd)
                    total_cost += cost
                    if returncode != 0:
                        break  # Stop if any command fails

                # calc affinity
                df_res_mode = get_affinity(dp_res_case, config)
                df_res_mode["cost_time"] = total_cost / len(df_res_mode) if len(df_res_mode) > 0 else total_cost
                df_res_mode["mode"] = search_mode
                # save results for this mode
                df_res_mode.to_csv(fp_res_mode, index=False)
                logging.info(f"{dataset}-{search_mode} finished")

            except:
                logging.error(traceback.format_exc())
            
            if df_res_mode is not None:
                df_res_dataset.append(df_res_mode)

        # save results for this dataset
        df_res_dataset = pd.concat(df_res_dataset, ignore_index=True)
        df_res_dataset["dataset"] = dataset
        df_res_dataset.to_csv(fp_res_dataset, index=False)

        df_res_all.append(df_res_dataset)

    # save results for all datasets
    df_res_all = pd.concat(df_res_all, ignore_index=True)
    df_res_all.to_csv(fp_res_all, index=False)
    analysis_metrics(dp_res)
