from typing import Dict, Any
from pathlib import Path
import os
import json
import copy
import traceback
import time
import subprocess as sp
from tqdm import tqdm

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)s]%(message)s',
)

import sys
sys.path.append(os.path.dirname(__file__))
from utils import calc_rmsd


DEFAULT_UNIDOCK_ARGS = {
    "scoring": "vina",
    "num_modes": "10",
    "verbosity": "2",
    "refine_step": "3",
    "seed": "181129",
}


def main(config: Dict[str, Any]):
    rootdir = Path(config.get("rootdir", ".")).resolve()
    savedir = Path(config.get("savedir", "results")).resolve()
    os.makedirs(savedir, exist_ok=True)
    round_num = config.get("round", 3)
    search_mode_list = config.get("srarch_mode_list", ["fast", "balance", "detail"])
    unidock_args = copy.deepcopy(DEFAULT_UNIDOCK_ARGS)
    unidock_args.update(config.get("unidock_args", dict()))

    if not os.path.exists(f"{rootdir}/data/molecular_docking"):
        logging.error(f"rootdir: {rootdir}/data/molecular_docking not found!")
        logging.info(os.listdir(rootdir))
        exit(-1)

    results = {}
    results_csv = "dataset,pdbid,mode,round,cost_time,status,Top1RMSD,Top1Success,Top3Success,Top10Success\n"
    # get datasets
    for _,datasets,_ in os.walk(f"{rootdir}/data/molecular_docking"): break
    for dataset in datasets:
        results[dataset] = {}
        # check dataset
        for _,pdbids,_ in os.walk(f"{rootdir}/data/molecular_docking/{dataset}"): break
        for search_mode in search_mode_list:
            for round in range(round_num):
                outdir = f"{savedir}/{dataset}-{search_mode}-{round}"
                os.makedirs(outdir, exist_ok=True)
                for pdbid in tqdm(pdbids, desc=f"{dataset}-{search_mode}-{round}"):
                    try:
                        # input files and params
                        datadir = Path(f"{rootdir}/data/molecular_docking/{dataset}/{pdbid}")
                        ligand = Path(f"{datadir}/{pdbid}_ligand_prep.sdf")
                        receptor = Path(f"{datadir}/{pdbid}_receptor.pdbqt")
                        with open(f"{datadir}/docking_grid.json", "r") as f:
                            pocket = json.load(f)
                        # command
                        cmd = [
                            "unidock",
                            "--receptor", str(receptor),
                            "--gpu_batch", str(ligand),
                            "--center_x", f"{pocket['center_x']:.4f}",
                            "--center_y", f"{pocket['center_y']:.4f}",
                            "--center_z", f"{pocket['center_z']:.4f}",
                            "--size_x", f"{pocket['size_x']:.4f}",
                            "--size_y", f"{pocket['size_y']:.4f}",
                            "--size_z", f"{pocket['size_z']:.4f}",
                            "--dir", str(outdir),
                            "--search_mode", search_mode,
                            "--keep_nonpolar_H",
                        ]
                        for k, v in unidock_args.items():
                            cmd += [f"--{k}", f"{v}"]
                        print(cmd)
                        # run
                        start_time = time.time()
                        status = sp.run(cmd, encoding="utf-8", capture_output=True)
                        end_time = time.time()
                        logging.debug(status.stdout)
                        if status.returncode != 0:
                            logging.error(status.stderr)
                        cost_time = end_time - start_time
                        # calc rmsd
                        out_ligand = Path(f"{outdir}/{pdbid}_ligand_prep_out.sdf")
                        ref_ligand = Path(f"{datadir}/{pdbid}_ligand_ori.sdf")
                        rmsd = calc_rmsd(ref_ligand, out_ligand)
                        # save results
                        results[dataset][pdbid] = results[dataset].get(pdbid, {})
                        results[dataset][pdbid][search_mode] = results[dataset][pdbid].get(search_mode, {})
                        results[dataset][pdbid][search_mode][round] = {
                            "cost_time": cost_time,
                            "status": status.returncode,
                            "RMSD": rmsd
                        }
                        results_csv += f"{dataset},{pdbid},{search_mode},{round},{cost_time},{status.returncode},"
                        results_csv += f"{rmsd[0]},{rmsd[0] < 2.0},{any(r < 2.0 for r in rmsd[:3])},{any(r < 2.0 for r in rmsd)}\n"
                    except:
                        logging.error(traceback.format_exc())
                        results[dataset][pdbid] = results[dataset].get(pdbid, {})
                        results[dataset][pdbid][search_mode] = results[dataset][pdbid].get(search_mode, {})
                        results[dataset][pdbid][search_mode][round] = {
                            "cost_time": None,
                            "status": -1,
                            "RMSD": None,
                        }

    with open(f"{savedir}/results.json", "w") as f:
        json.dump(results, f, indent=4)

    with open(f"{savedir}/results.csv", "w") as f:
        f.write(results_csv)

    info = "dataset,mode,round,success_rate,avr_time\n"
    logging.info("[dataset][mode]\t[success]\t[avr_time]")
    for dataset in results:
        for mode in search_mode_list:
            for round in range(round_num):
                success_rate = sum(results[dataset][pdbid][mode][round]["RMSD"][0] < 2.0 \
                    for pdbid in results[dataset]) / len(results[dataset])
                avr_time = sum(results[dataset][pdbid][mode][round]["cost_time"] \
                    for pdbid in results[dataset]) / len(results[dataset])
                info += f"{dataset},{mode},{round},{success_rate:.6f},{avr_time:.6f}\n"
                logging.info(f"[{dataset}][{mode}][{round}]\t{success_rate:.6f}\t{avr_time:.6f}")

    with open(f"{savedir}/metrics.csv", "w") as f:
        f.write(info)

    return

def main_cli():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument("--rootdir", type=str, default=None)
    parser.add_argument("--savedir", type=str, default="results")
    parser.add_argument("--round", type=int, default=3)
    args = parser.parse_args()
    
    if args.config_file is not None:
        with open(args.config_file) as f:
            config = json.load(f)
    else:
        if args.rootdir is None:
            if os.path.exists("../data/molecular_docking"):
                rootdir = Path("..").resolve()
            if os.path.exists("./data/molecular_docking"):
                rootdir = Path(".").resolve()
        else:
            rootdir = Path(args.rootdir).resolve()
            if not os.path.exists(f"{rootdir}/data/molecular_docking"):
                logging.error(f"rootdir: {rootdir}/data/molecular_docking not found!")
                exit(-1)
    
        config = {"rootdir": rootdir, "savedir": args.savedir, "round": args.round}
    
    main(config)


if __name__ == "__main__":
    main_cli()
