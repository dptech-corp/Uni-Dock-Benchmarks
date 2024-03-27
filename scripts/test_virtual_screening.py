from pathlib import Path
import os
import copy
import subprocess as sp
import traceback
import time
import json
import glob
import shutil
from tqdm import tqdm

import sys

sys.path.append("../")

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s][%(levelname)s]%(message)s",
)

from utils import makedirs


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
    search_mode_list = config.get("search_mode_list", ["fast", "balance", "detail"])
    unidock_args = copy.deepcopy(DEFAULT_UNIDOCK_ARGS)
    unidock_args.update(config.get("unidock_args", dict()))

    if not os.path.exists(f"{rootdir}/data/molecular_docking"):
        logging.error(f"rootdir: {rootdir}/data/molecular_docking not found!")
        logging.info(os.listdir(rootdir))
        exit(-1)

    results_csv = "dataset,mode,total_num,success_num,cost_time,avg_time_per_ligand\n"
    # get datasets
    for _, datasets, _ in os.walk(f"{rootdir}/data/virtual_screening"):
        break
    if config.get("dataset_names"):
        datasets = [d for d in datasets if d in config.get("dataset_names", [])]
    logging.info(f"Running datasets: {datasets}")
    for dataset in datasets:
        # split data
        temp_dir = makedirs(prefix=f"{savedir}/{dataset}", date=True, randomID=True)
        ligand_path_list = []
        with open(
            Path(f"{rootdir}/data/virtual_screening/{dataset}/actives.sdf"), "r"
        ) as f:
            actives = f.read().split("$$$$\n")
        for idx, active in enumerate(actives):
            if active:
                with open(Path(f"{temp_dir}/active-{idx}.sdf"), "w") as f:
                    f.write(active + "$$$$\n")
                ligand_path_list.append(f"{temp_dir}/active-{idx}.sdf")
        with open(
            Path(f"{rootdir}/data/virtual_screening/{dataset}/inactives.sdf"), "r"
        ) as f:
            inactives = f.read().split("$$$$\n")
        for idx, inactive in enumerate(inactives):
            if inactive:
                with open(Path(f"{temp_dir}/inactive-{idx}.sdf"), "w") as f:
                    f.write(inactive + "$$$$\n")
                ligand_path_list.append(f"{temp_dir}/inactive-{idx}.sdf")
        total_num = len(ligand_path_list)
        logging.info(f"Ligands num: {total_num}")
        with open(Path(f"{temp_dir}/ligand_list.txt"), "w") as f:
            f.write("\n".join(ligand_path_list))
        # check dataset
        for search_mode in search_mode_list:
            outdir = f"{savedir}/{dataset}-{search_mode}"
            os.makedirs(outdir, exist_ok=True)
            datadir = f"{rootdir}/data/virtual_screening/{dataset}"
            try:
                # input files and params
                receptor = glob.glob(
                    f"{rootdir}/data/virtual_screening/{dataset}/*_receptor.pdbqt"
                )[0]
                with open(f"{datadir}/docking_grid.json", "r") as f:
                    pocket = json.load(f)
                # command
                cmd_line = (
                    f"unidock --receptor {receptor} --ligand_index {temp_dir}/ligand_list.txt "
                    f"--center_x {pocket['center_x']:.4f} --center_y {pocket['center_y']:.4f} --center_z {pocket['center_z']:.4f} "
                    f"--size_x {pocket['size_x']:.4f} --size_y {pocket['size_y']:.4f} --size_z {pocket['size_z']:.4f} "
                    f"--dir {outdir} --search_mode {search_mode} --keep_nonpolar_H "
                )
                cmd = cmd_line.split()
                for k, v in unidock_args.items():
                    cmd += [f"--{k} {v}"]
                # run
                start_time = time.time()
                status = sp.run(cmd, capture_output=True, encoding="utf-8")
                end_time = time.time()
                if status.returncode != 0:
                    logging.info(status.stdout)
                    logging.error(status.stderr)
                cost_time = end_time - start_time
                logging.info(
                    f"dataset {dataset} mode {search_mode} cost time: {cost_time}"
                )

                # save results
                result_ligands = glob.glob(f"{outdir}/*_out.sdf")
                success_num = len(result_ligands)
                logging.info(
                    f"dataset {dataset} mode {search_mode} success num: {success_num}"
                )
                content_list = []
                for result_ligand in result_ligands:
                    with open(result_ligand, "r") as f:
                        content_list.append(f.read())
                with open(f"./{dataset}_{search_mode}_results.sdf", "w") as f:
                    f.write("".join(content_list))

                results_csv += f"{dataset},{search_mode},{total_num},{success_num},{cost_time},{cost_time/len(ligand_path_list)}\n"
                shutil.rmtree(outdir, ignore_errors=True)
            except:
                logging.error(traceback.format_exc())
                results_csv += f"{dataset},{search_mode},{total_num},0,0,0\n"

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
            import wget
            wget.download(
                "https://bohrium-api.dp.tech/ds-dl/GBA-inactives-ap7r-v2.zip",
                out=f"{rootdir}/data/virtual_screening/GBA/inactives.zip",
            )
            shutil.unpack_archive(
                f"{rootdir}/data/virtual_screening/GBA/inactives.zip",
                extract_dir=f"{rootdir}/data/virtual_screening/GBA",
            )

        config = {"rootdir": rootdir, "savedir": args.savedir}

    main(config)


if __name__ == "__main__":
    main_cli()
