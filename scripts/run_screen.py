"""
Author: Congcong Liu
Brief: 
task: virtual screening
https://github.com/dptech-corp/Uni-Dock-Benchmarks

Updated: 2025-06-05
"""

import os
import traceback
import pandas as pd
import logging

from engines.base import DockingEngine
from utils.myio import read_json
from utils.config import CSV_NAME
from utils.common import prepare_dirs, run_command, check_rerun


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


def run_benchmark_virtual_screening(engine: DockingEngine, rerun: bool = True):
    """
    Run virtual screening benchmark.
    
    Args:
        engine: DockingEngine instance (V1 or V2)
        rerun: Whether to rerun if results already exist
    """
    config = engine.config
    dp_data, dp_res = prepare_dirs(config)

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
        for search_mode in engine.search_modes:
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
                dp_res_case = os.path.join(dp_res_mode, "tmp")
                os.makedirs(dp_res_case, exist_ok=True)
                fp_center = os.path.join(dp_data_dataset, "docking_grid.json")
                data_center = read_json(fp_center)

                list_cmd = engine.build_screen_commands(
                    dp_data_dataset, dataset, data_center,
                    dp_res_case, search_mode,
                )
                total_cost = 0.0
                for cmd in list_cmd:
                    returncode, cost, stdout, stderr = run_command(cmd)
                    total_cost += cost
                    if returncode != 0:
                        break  # Stop if any command fails

                affinity_results = engine.parse_screen_affinity(dp_res_case)
                df_res_mode = pd.DataFrame(
                    affinity_results, columns=["Ligand", "Affinity", "Active"],
                )
                # Save intermediate per-case results
                fp_res_tmp = os.path.join(dp_res_case, CSV_NAME)
                df_res_mode.to_csv(fp_res_tmp, index=False)

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
