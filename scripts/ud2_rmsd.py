"""
Compute RMSD for ud2 engine output.
Expected: in a Astex result directory, the relative path contains pdb_id
  using input config file to find the reference ligand
  using output json to generate sdf and then compute rmsd
"""
import sys  
import os
import yaml
import argparse
from utils import config
from utils.calc_rmsd import tran_json_to_sdf, calc_rmsd

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("res", type=str, default=None, help="standard ud2 dir")
    parser.add_argument("--data", type=str, default=None, help="original sdf file")
    args = parser.parse_args()
    
    dp = args.res
    fp_res_json = os.path.join(dp, [i for i in os.listdir(dp) if i.endswith("json")][0])
    fp_config = os.path.join(dp, [i for i in os.listdir(dp) if i.endswith("yaml")][0])
    fp_res_sdf = os.path.join(dp, "ud2.sdf")

    if args.data is None:
        with open(fp_config, "r") as f:
            data = yaml.safe_load(f)
        dp_ligand = os.path.dirname(os.path.dirname(data["Inputs"]["json"]))
    else:
        dp_ligand = args.data

    dataset = "Astex"
    id_pdb = dp_ligand.strip().split("/")[-1].strip()

    fp_ligand_input = os.path.join(dp_ligand, config.FMT_UD2[dataset]["sdf"].format(id_pdb))
    fp_ligand_ref = os.path.join(dp_ligand, f"{id_pdb}_ligand.sdf")

    tran_json_to_sdf(fp_res_json, fp_ligand_input, fp_res_sdf)
    list_rmsd = calc_rmsd(fp_ligand_ref, fp_res_sdf)
    print("RMSD is: \n", list_rmsd)