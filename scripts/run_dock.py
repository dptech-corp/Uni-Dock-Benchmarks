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

from utils.calc_rmsd import calc_rmsd, tran_json_to_sdf
from utils.config import BenchmarkConfig, FMT_UD1, FMT_UD2, CSV_NAME
from utils.common import prepare_dirs, gen_cmd_ud2, run_command, check_rerun

#------------------------ Uni-Dock V1 ------------------------    

def gen_cmd_ud1(fp_ligand, fp_receptor, data_center, dp_res_case, search_mode, config: BenchmarkConfig, rand=False):
    """Generate command for Uni-Dock V1."""
    base_cmd = [
        config.binary,
        "--receptor", str(fp_receptor),
        "--gpu_batch", str(fp_ligand),
        "--center_x", f"{data_center['X']:.1f}",
        "--center_y", f"{data_center['Y']:.1f}",
        "--center_z", f"{data_center['Z']:.1f}",
        "--size_x", f"{30.0:.1f}",
        "--size_y", f"{30.0:.1f}",
        "--size_z", f"{30.0:.1f}",
        "--dir", str(dp_res_case),
        "--keep_nonpolar_H",
        "--device_id", str(config.device_id),
        "--cpu", "32",
        "--seed", str(config.seed),
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
def gen_cmd(dp_data_id, dataset, id_pdb, data_center, dp_res_case, search_mode, config: BenchmarkConfig):
    """Generate command based on version."""
    if config.version == 1:
        fp_ligand = os.path.join(dp_data_id, FMT_UD1[dataset]["sdf"].format(config.fn_suffix, id_pdb))
        fp_receptor = os.path.join(dp_data_id, FMT_UD1[dataset]["pdb"].format(config.fn_suffix, id_pdb))
        return gen_cmd_ud1(fp_ligand, fp_receptor, data_center, dp_res_case, search_mode, config)
    elif config.version == 2:
        fp_json = os.path.join(dp_data_id, FMT_UD2[dataset]["json"].format(config.fn_suffix, id_pdb))    
        return gen_cmd_ud2(fp_json, data_center, dp_res_case, search_mode, config, use_log=True, center_format="molecular_docking")


def cal_rmsd(dp_data_id, dataset, id_pdb, dp_res_case, config: BenchmarkConfig):
    """Calculate RMSD for molecular docking results."""
    fp_ligand_ref = os.path.join(dp_data_id, f"{id_pdb}_ligand.sdf")

    if config.version == 1:
        fp_ligand_out = os.path.join(dp_res_case, FMT_UD1[dataset]["out"].format(config.fn_suffix, id_pdb))
        list_rmsd = calc_rmsd(fp_ligand_ref, fp_ligand_out)
    elif config.version == 2:
        fp_ligand_input = os.path.join(dp_data_id, FMT_UD2[dataset]["sdf"].format(config.fn_suffix, id_pdb))
        fp_res_json = os.path.join(dp_res_case, FMT_UD2[dataset]["out"].format(config.fn_suffix, id_pdb))
        fp_res_sdf = os.path.join(dp_res_case, "ud2_1.sdf")
        tran_json_to_sdf(fp_res_json, fp_ligand_input, fp_res_sdf)
        list_rmsd = calc_rmsd(fp_ligand_ref, fp_res_sdf)
    return list_rmsd   



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


def run_benchmark_molecular_docking(config: BenchmarkConfig, rerun: bool = True):
    """
    Run molecular docking benchmark.
    
    Args:
        config: BenchmarkConfig object containing all benchmark settings
        rerun: Whether to rerun if results already exist
    """
    
    
    dp_data, dp_res = prepare_dirs(config)
    search_mode_list = config.search_mode_list

    # Start Benchmark Test
    columns_res = ["dataset", "pdbid", "mode", "cost_time", "status", "Top1RMSD", "Top1Success", "Top10Success"]

    fp_res_all = os.path.join(dp_res, CSV_NAME)
    df_res_all = pd.DataFrame(columns=columns_res)

    # For each dataset
    for dataset in sorted(os.listdir(dp_data)):
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
        for search_mode in search_mode_list:
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

                    # command
                    cmd = gen_cmd(dp_data_id, dataset, id_pdb, data_center[id_pdb], dp_res_case, search_mode, config)
                    # run
                    returncode, cost, stdout, stderr = run_command(cmd)

                    # calc rmsd
                    rmsds = cal_rmsd(dp_data_id, dataset, id_pdb, dp_res_case, config)

                    # df_res_mode add one row
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
