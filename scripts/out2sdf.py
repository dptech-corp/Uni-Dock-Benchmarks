"""
Convert ud2 output JSON file into SDF file.
"""
import os
import argparse
from utils.calc_rmsd import tran_json_to_sdf

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ori", type=str, default=None, help="original sdf file")
    parser.add_argument("--json", type=str, default=None, help="json file")
    parser.add_argument("--out", type=str, default=None, help="output sdf file path")
    parser.add_argument("--name", type=str, default=None, help="molecule name")
    parser.add_argument("--noH", action="store_true", help="remove Hydrogen atoms")
    args = parser.parse_args()


    fp_res_json = os.path.abspath(args.json)
    fp_ligand_input = os.path.abspath(args.ori)
    if args.out is None:
        fp_res_sdf = os.path.join(os.path.dirname(fp_res_json), "json2.sdf")
    else:
        fp_res_sdf = os.path.abspath(args.out)
    
    tran_json_to_sdf(fp_res_json, fp_ligand_input, fp_res_sdf, args.noH, args.name)
