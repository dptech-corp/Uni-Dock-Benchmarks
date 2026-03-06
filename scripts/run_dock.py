"""
Author: Congcong Liu
Brief: 
task: molecular docking
https://github.com/dptech-corp/Uni-Dock-Benchmarks

Updated: 2025-06-05
"""
import os
import traceback
from tqdm import tqdm
import pandas as pd
import logging

from engines.base import DockingEngine
from utils.config import CSV_NAME
from utils.common import prepare_dirs, run_command, check_rerun


def analysis_metrics(dp_res: str):
    """
    For given dp_res, calculate the metrics of all datasets and modes
    """
    fp_res = os.path.join(dp_res, CSV_NAME)
    df_res = pd.read_csv(fp_res)

    fp_metrics = os.path.join(dp_res, "metrics.csv")
    columns = ["dataset", "mode", "failed_num", "total_num", "hit_rate_rmsd2.0", "avr_time(s)"]

    list_data_metrics = []
    for dataset in df_res["dataset"].unique():
        for mode in df_res["mode"].unique():
            df_mode = df_res[(df_res["dataset"] == dataset) & (df_res["mode"] == mode)]
            failed_num = df_mode[df_mode["status"] == -1].shape[0]
            total_num = df_mode.shape[0]
            hit_rate_rmsd2 = df_mode[df_mode["Top1RMSD"] < 2.0].shape[0] / total_num if total_num > 0 else 0.0
            avr_time = df_mode["cost_time"].mean()
            list_data_metrics.append([dataset, mode, failed_num, total_num, hit_rate_rmsd2, avr_time])

    df_metrics = pd.DataFrame(list_data_metrics, columns=columns)
    df_metrics.to_csv(fp_metrics, index=False, float_format='%.3f')


def run_benchmark_molecular_docking(engine: DockingEngine, rerun: bool = True, datasets=None):
    """
    Run molecular docking benchmark.
    
    Args:
        engine: DockingEngine instance (V1 or V2)
        rerun: Whether to rerun if results already exist
        datasets: List of dataset names to run (e.g. ['Astex']). None means all.
    """
    config = engine.config
    dp_data, dp_res = prepare_dirs(config)

    columns_res = ["dataset", "pdbid", "mode", "cost_time", "status", "Top1RMSD", "Top1Success", "Top10Success"]

    fp_res_all = os.path.join(dp_res, CSV_NAME)
    df_res_all = pd.DataFrame(columns=columns_res)

    all_datasets = sorted(os.listdir(dp_data))
    if datasets:
        all_datasets = [d for d in all_datasets if d in datasets]

    # For each dataset
    for dataset in all_datasets:
        dp_data_dataset = os.path.join(dp_data, dataset)
        # read csv file
        fp_center = os.path.join(dp_data_dataset, "pdb_center.csv")
        data_center = pd.read_csv(fp_center).set_index('PDB_ID').to_dict('index')
        ids_pdb = [i for i in sorted(os.listdir(dp_data_dataset)) if os.path.isdir(os.path.join(dp_data_dataset, i))]

        dp_res_dataset = os.path.join(dp_res, dataset)
        os.makedirs(dp_res_dataset, exist_ok=True)
        fp_res_dataset = os.path.join(dp_res_dataset, CSV_NAME)
        df_res_dataset = pd.DataFrame(columns=columns_res)
        # For each search mode
        for search_mode in engine.search_modes:
            dp_res_mode = os.path.join(dp_res_dataset, search_mode)
            os.makedirs(dp_res_mode, exist_ok=True)
            fp_res_mode = os.path.join(dp_res_mode, CSV_NAME)
            
            if not check_rerun(fp_res_mode, rerun):
                # Load existing results if not rerunning
                if os.path.exists(fp_res_mode):
                    df_res_mode = pd.read_csv(fp_res_mode)
                    df_res_dataset = pd.concat([df_res_dataset, df_res_mode], ignore_index=True)
                continue

            list_res_mode = []
            # For each pdbid
            for id_pdb in tqdm(ids_pdb, desc=f"{dataset}-{search_mode}", leave=True):
                dp_data_id = os.path.join(dp_data_dataset, id_pdb)
                try:
                    # Start test on this case
                    dp_res_case = os.path.join(dp_res_mode, id_pdb)
                    os.makedirs(dp_res_case, exist_ok=True)

                    cmd = engine.build_dock_command(
                        dp_data_id, dataset, id_pdb,
                        data_center[id_pdb], dp_res_case, search_mode,
                    )
                    returncode, cost, stdout, stderr = run_command(cmd)

                    rmsds = engine.compute_dock_rmsd(
                        dp_data_id, dataset, id_pdb, dp_res_case,
                    )

                    list_res_mode.append([dataset, id_pdb, search_mode, cost, returncode, 
                        rmsds[0], rmsds[0] < 2.0, any(r < 2.0 for r in rmsds)]
                    )
                    logging.info(f"{id_pdb} finished")

                except:
                    list_res_mode.append([dataset, id_pdb, search_mode, None, -1, 
                        None, None, None]
                    )
                    logging.error(traceback.format_exc())

            df_res_mode = pd.DataFrame(list_res_mode, columns=columns_res)
            df_res_mode.to_csv(fp_res_mode, index=False)
            
            # save results for this mode
            df_res_dataset = pd.concat([df_res_dataset, df_res_mode], ignore_index=True)

        # save results for this dataset
        df_res_dataset.to_csv(fp_res_dataset, index=False)
        df_res_all = pd.concat([df_res_all, df_res_dataset], ignore_index=True)

    # save results for all datasets
    df_res_all.to_csv(fp_res_all, index=False)
    analysis_metrics(dp_res)
