import os
from tqdm import tqdm
from pathlib import Path
import subprocess as sp
import traceback
import time
import json
import glob
import shutil

import sys
sys.path.append("../")

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)s]%(message)s',
)

from utils import makedirs


def main(config):
    results_csv = "dataset,mode,cost_time,avr_time\n"
    rootdir = Path(config.get("rootdir", ".")).resolve()
    # check savedir
    savedir = Path(config.get("savedir", "results")).resolve()
    if not os.path.exists(savedir):
        savedir = makedirs(prefix=savedir, date=True, randomID=True)
    # get datasets
    for _,datasets,_ in os.walk(f"{rootdir}/data/virtual_screening"): break
    for dataset in datasets:
        # split data
        temp_dir = makedirs(prefix=f"{savedir}/{dataset}", date=True, randomID=True)
        ligand_path_list = []
        with open(Path(f"{rootdir}/data/virtual_screening/{dataset}/actives.sdf"), "r") as f:
            actives = f.read().split("$$$$\n")
        for idx, active in enumerate(actives):
            with open(Path(f"{temp_dir}/active-{idx}.sdf"), "w") as f:
                f.write(active + "$$$$\n")
            ligand_path_list.append(f"{temp_dir}/active-{idx}.sdf")
        with open(Path(f"{rootdir}/data/virtual_screening/{dataset}/inactives.sdf"), "r") as f:
            inactives = f.read().split("$$$$\n")
        for idx, inactive in enumerate(inactives):
            with open(Path(f"{temp_dir}/inactive-{idx}.sdf"), "w") as f:
                f.write(inactive + "$$$$\n")
            ligand_path_list.append(f"{temp_dir}/inactive-{idx}.sdf")
        with open(Path(f"{temp_dir}/ligand_list.txt"), "w") as f:
            f.write("\n".join(ligand_path_list))
        # check dataset
        for search_mode in ["fast", "balance", "detail"]:
            outdir = f"{savedir}/{dataset}-{search_mode}"
            os.makedirs(outdir, exist_ok=True)
            datadir = f"{rootdir}/data/virtual_screening/{dataset}"
            try:
                # input files and params
                receptor = glob.glob(f"{rootdir}/data/virtual_screening/{dataset}/*_receptor.pdbqt")[0]
                with open(f"{datadir}/docking_grid.json", "r") as f:
                    pocket = json.load(f)
                # command
                cmd = [
                    "unidock",
                    "--receptor", str(receptor),
                    "--ligand_index", str(f"{temp_dir}/ligand_list.txt"),
                    "--center_x", f"{pocket['center_x']:.4f}",
                    "--center_y", f"{pocket['center_y']:.4f}",
                    "--center_z", f"{pocket['center_z']:.4f}",
                    "--size_x", f"{pocket['size_x']:.4f}",
                    "--size_y", f"{pocket['size_y']:.4f}",
                    "--size_z", f"{pocket['size_z']:.4f}",
                    "--dir", str(outdir),
                    "--search_mode", search_mode,
                    "--scoring", "vina",
                    "--num_modes", "1",
                    "--verbosity", "2",
                    "--refine_step", "3",
                    "--keep_nonpolar_H",
                    "--seed", "181129",
                ]
                # run
                start_time = time.time()
                status = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
                end_time = time.time()
                cost_time = end_time - start_time
                # save results
                results_csv += f"{dataset},{search_mode},{cost_time},{cost_time/len(ligand_path_list)}\n"
            except:
                logging.error(traceback.format_exc())
                results_csv += f"{dataset},{search_mode},-1,-1\n"
                    
        shutil.rmtree(temp_dir)
    
    with open(f"{savedir}/results.csv", "w") as f:
        f.write(results_csv)
        
    return 


def main_cli():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rootdir", type=str, default=None)
    parser.add_argument("--savedir", type=str, default=None)
    parser.add_argument("--round", type=int, default=3)
    args = parser.parse_args()
    
    if args.rootdir is None:
        if os.path.exists("../data/virtual_screening"):
            rootdir = Path("..").resolve()
        if os.path.exists("./data/virtual_screening"):
            rootdir = Path(".").resolve()
    else:
        rootdir = Path(args.rootdir).resolve()
        if not os.path.exists(f"{rootdir}/data/virtual_screening"):
            logging.error(f"rootdir: {rootdir}/data/virtual_screening not found!")
            exit(-1)
    
    if not os.path.exists(f"{rootdir}/data/virtual_screening/GBA/inactives.sdf"):
        wget.download(
            "https://bohrium-api.dp.tech/ds-dl/GBA-inactives-ap7r-v1.zip", 
            out=f"{rootdir}/data/virtual_screening/GBA/inactives.zip")
        sp.run(f"unzip {rootdir}/data/virtual_screening/GBA/inactives.zip -d {rootdir}/data/virtual_screening/GBA".split())
    
    config = {"rootdir": rootdir, "savedir": args.savedir, "round": args.round}
    
    main(config)
    

if __name__ == "__main__":
    main_cli()