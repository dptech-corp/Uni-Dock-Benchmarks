#!python
"""
Convert ud2 output JSON file into input JSON file.
"""
import os
from utils.myio import *
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ori", type=str, default=None, help="original input json")
    parser.add_argument("--out", type=str, default=None, help="output json file")
    parser.add_argument("--newin", type=str, default=None, help="input json file with the first pose in output json")
    parser.add_argument("--i", type=int, default=0, help="indice of the pose to transfer")
    args = parser.parse_args()


    fp_out = os.path.abspath(args.out)
    fp_ori = os.path.abspath(args.ori)

    if args.newin is None:
        fp_newin = os.path.join(os.path.dirname(fp_out), "newin.json")
    else:
        fp_newin = os.path.abspath(args.newin)
    
    # read the original json
    data = read_json(fp_ori)
    k = list(set(data.keys()) - {"receptor", "score"})[0]

    # read the output json
    pose = list(read_json(fp_out).values())[0][args.i]

    # merge the two dictionary
    # coords
    for i in range(len(data[k]["atoms"])):
        data[k]["atoms"][i][0] = pose["coords"][i * 3]
        data[k]["atoms"][i][1] = pose["coords"][i * 3 + 1]
        data[k]["atoms"][i][2] = pose["coords"][i * 3 + 2]
    
    # dihedrals
    for i in range(len(data[k]["torsions"])):
        data[k]["torsions"][i][1] = pose["dihedrals"][i]
    
    # write newin
    write_json(data, fp_newin)
