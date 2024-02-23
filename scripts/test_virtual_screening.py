from pathlib import Path
import os
import copy
import subprocess as sp
import traceback
import time
import json
import glob
import shutil
import wget
from tqdm import tqdm

import sys
sys.path.append("../")

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s][%(levelname)s]%(message)s',
)

from utils import makedirs, read_unidock_score, ef_score


DEFAULT_UNIDOCK_ARGS = {
    "scoring": "vina",
    "num_modes": "1",
    "verbosity": "2",
    "refine_step": "3",
    "seed": "181129",
}

EF_FRACTION_LIST = [0.005, 0.01, 0.05, 0.1, 0.2]


def main(config):
    rootdir = Path(config.get("rootdir", ".")).resolve()
    savedir = Path(config.get("savedir", "results")).resolve()
    os.makedirs(savedir, exist_ok=True)
    search_mode_list = config.get("srarch_mode_list", ["fast", "balance", "detail"])
    unidock_args = copy.deepcopy(DEFAULT_UNIDOCK_ARGS)
    unidock_args.update(config.get("unidock_args", dict()))

    if not os.path.exists(f"{rootdir}/data/molecular_docking"):
        logging.error(f"rootdir: {rootdir}/data/molecular_docking not found!")
        logging.info(os.listdir(rootdir))
        exit(-1)

    results_csv = "dataset,mode,cost_time,avg_time_per_ligand,ef_0.005,ef_0.01,ef_0.05,ef_0.1,ef_0.2\n"
    # get datasets
    for _,datasets,_ in os.walk(f"{rootdir}/data/virtual_screening"): break
    for dataset in datasets:
        # split data
        temp_dir = makedirs(prefix=f"{savedir}/{dataset}", date=True, randomID=True)
        ligand_path_list = []
        with open(Path(f"{rootdir}/data/virtual_screening/{dataset}/actives.sdf"), "r") as f:
            actives = f.read().split("$$$$\n")
        for idx, active in enumerate(actives):
            if active:
                with open(Path(f"{temp_dir}/active-{idx}.sdf"), "w") as f:
                    f.write(active + "$$$$\n")
                ligand_path_list.append(f"{temp_dir}/active-{idx}.sdf")
        with open(Path(f"{rootdir}/data/virtual_screening/{dataset}/inactives.sdf"), "r") as f:
            inactives = f.read().split("$$$$\n")
        for idx, inactive in enumerate(inactives):
            if inactive:
                with open(Path(f"{temp_dir}/inactive-{idx}.sdf"), "w") as f:
                    f.write(inactive + "$$$$\n")
                ligand_path_list.append(f"{temp_dir}/inactive-{idx}.sdf")
        with open(Path(f"{temp_dir}/ligand_list.txt"), "w") as f:
            f.write("\n".join(ligand_path_list))
        # check dataset
        for search_mode in search_mode_list:
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
                    "--keep_nonpolar_H",
                ]
                for k, v in unidock_args.items():
                    cmd += [f"--{k}", f"{v}"]
                print(cmd)
                # run
                start_time = time.time()
                status = sp.run(cmd, capture_output=True, encoding="utf-8")
                end_time = time.time()
                logging.debug(status.stdout)
                if status.returncode != 0:
                    logging.error(status.stderr)
                cost_time = end_time - start_time

                # calc
                result_ligands = glob.glob(f"{outdir}/*_out.sdf")
                label_list, score_list = [], []
                for result_ligand in result_ligands:
                    label = 1 if Path(result_ligand).stem.startswith("active") else 0
                    score = read_unidock_score(result_ligand)[0]
                    label_list.append(label)
                    score_list.append(score)
                
                ef_scores = ef_score(label_list, score_list, EF_FRACTION_LIST)
                # save results
                results_csv += f"{dataset},{search_mode},{cost_time},{cost_time/len(ligand_path_list)},{ef_scores[0]},{ef_scores[1]},{ef_scores[2]},{ef_scores[3]},{ef_scores[4]}\n"
            except:
                logging.error(traceback.format_exc())
                results_csv += f"{dataset},{search_mode},-1,-1,0,0,0,0,0\n"
                    
        shutil.rmtree(temp_dir)
        logging.info(f"dataset {dataset} finished")
    
    with open(f"{savedir}/results.csv", "w") as f:
        f.write(results_csv)

    return


def main_cli():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file", type=str, default=None)
    parser.add_argument("--rootdir", type=str, default=None)
    parser.add_argument("--savedir", type=str, default="results")
    args = parser.parse_args()

    if args.config_file is not None:
        with open(args.config_file) as f:
            config = json.load(f)
    else:
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
        
        if not os.path.exists(f"{rootdir}/virtual_screening/GBA/inactives.sdf"):
            wget.download(
                "https://bohrium-api.dp.tech/ds-dl/GBA-inactives-ap7r-v1.zip", 
                out=f"{rootdir}/data/virtual_screening/GBA/inactives.zip")
            sp.run(f"unzip {rootdir}/data/virtual_screening/GBA/inactives.zip -d {rootdir}/data/virtual_screening/GBA", shell=True)
        
        config = {"rootdir": rootdir, "savedir": args.savedir}
    
    main(config)


if __name__ == "__main__":
    main_cli()
