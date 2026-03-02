"""
Legacy / currently-unused helpers.

This file stores code paths that are not part of the current benchmark
pipeline but may still be useful for ad-hoc debugging.
"""

import json
import logging
import os
import traceback

import pandas as pd
from rdkit.ML.Scoring.Scoring import CalcEnrichment
from tqdm import tqdm


def read_ud1_score(result_file: str) -> list[float]:
    score_list = []
    with open(result_file, "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.startswith("> <Uni-Dock RESULT>"):
                score = float(lines[idx + 1].partition("LOWER_BOUND=")[0][len("ENERGY="):])
                score_list.append(score)
    return score_list


def ef_score(
    label_list: list[int],
    score_list: list[float],
    fraction_list: list[float],
    sort_flag: bool = False,
):
    assert len(label_list) == len(score_list), "Number of label and score list not match"
    assert len(fraction_list) > 0, "need to assign the fractions of enrichment"
    assert all([v in [0, 1] for v in label_list]), "label list should be binary"

    label_score_list = list(zip(label_list, score_list))
    label_score_list = sorted(label_score_list, key=lambda pair: pair[1], reverse=sort_flag)
    return CalcEnrichment(label_score_list, 0, fraction_list)


def cal_rmsd_ud2(fp_ligand_ref, fp_res_json, fp_ligand_input):
    from rdkit.Chem import AllChem as Chem
    from rdkit.Chem import rdMolAlign
    import numpy as np

    with open(fp_res_json, "r") as f:
        json_res = json.load(f)

    ligand_name = list(json_res.keys())[0]
    assert len(ligand_name) > 0, "ligand_name not found!"

    mol_ref = Chem.SDMolSupplier(str(fp_ligand_ref), removeHs=True)[0]
    mol_input = Chem.SDMolSupplier(str(fp_ligand_input), removeHs=False)[0]

    list_rmsd = []
    for pose in json_res[ligand_name]:
        mol_res = Chem.Mol(mol_input)
        conf = mol_res.GetConformer()

        coords_res = np.array(pose["coords"]).reshape(-1, 3)
        for i in range(conf.GetNumAtoms()):
            conf.SetAtomPosition(i, coords_res[i])

        mol_res = Chem.RemoveAllHs(mol_res)
        rmsd = rdMolAlign.CalcRMS(mol_ref, mol_res)
        list_rmsd.append(rmsd)

    return list_rmsd


def rerun_rmsd_update_results(dp_res: str, dp_data: str, config):
    """
    Legacy helper from old molecular docking debug workflow.
    """
    from run_dock import analysis_metrics, cal_rmsd
    from utils.config import CSV_NAME

    fp_res_all = os.path.join(dp_res, CSV_NAME)
    df_res_all = pd.DataFrame()

    for dataset in sorted(os.listdir(dp_res)):
        dp_res_dataset = os.path.join(dp_res, dataset)
        if not os.path.isdir(dp_res_dataset):
            continue

        dp_data_dataset = os.path.join(dp_data, dataset)
        fp_res_dataset = os.path.join(dp_res_dataset, CSV_NAME)
        df_res_dataset = pd.DataFrame()

        for search_mode in sorted(os.listdir(dp_res_dataset)):
            dp_res_mode = os.path.join(dp_res_dataset, search_mode)
            if not os.path.isdir(dp_res_mode):
                continue

            fp_res_mode = os.path.join(dp_res_mode, CSV_NAME)
            if not os.path.exists(fp_res_mode):
                continue

            df_res_mode = pd.read_csv(fp_res_mode)
            for id_pdb in tqdm(df_res_mode["pdbid"].unique(), desc=f"{dataset}-{search_mode}", leave=True):
                dp_data_id = os.path.join(dp_data_dataset, id_pdb)
                try:
                    dp_res_case = os.path.join(dp_res_mode, id_pdb)
                    rmsds = cal_rmsd(dp_data_id, dataset, id_pdb, dp_res_case, config)
                    df_res_mode.loc[df_res_mode["pdbid"] == id_pdb, "Top1RMSD"] = rmsds[0]
                    df_res_mode.loc[df_res_mode["pdbid"] == id_pdb, "Top1Success"] = rmsds[0] < 2.0
                    df_res_mode.loc[df_res_mode["pdbid"] == id_pdb, "Top10Success"] = any(r < 2.0 for r in rmsds)
                    logging.info("%s finished", id_pdb)
                except Exception:
                    logging.error(traceback.format_exc())

            df_res_mode.to_csv(fp_res_mode, index=False)
            df_res_dataset = pd.concat([df_res_dataset, df_res_mode], ignore_index=True)

        df_res_dataset.to_csv(fp_res_dataset, index=False)
        df_res_all = pd.concat([df_res_all, df_res_dataset], ignore_index=True)

    df_res_all.to_csv(fp_res_all, index=False)
    analysis_metrics(dp_res)
