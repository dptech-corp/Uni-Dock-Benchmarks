from pathlib import Path
from rdkit.Chem import AllChem as Chem
from rdkit.Chem import rdMolAlign
import json
import numpy as np

def calc_rmsd(
    ref_ligand: Path, 
    target_ligand: Path,
):
    ref_mol = Chem.SDMolSupplier(str(ref_ligand), removeHs=True)[0]
    target_mols = Chem.SDMolSupplier(str(target_ligand), removeHs=True)
    return [rdMolAlign.CalcRMS(ref_mol, tmol) for tmol in target_mols]



def tran_json_to_sdf(fp_res_json, fp_sdf, fp_res_sdf, noH=False, new_name=None):
    # fixme: The atom order in fp_res_json is different from the original fp_sdf
    """ Use RDKit to perform an align&rmsd process, without Hydrogen """
    with open(fp_res_json, "r") as f:
        json_res = json.load(f)

    # fp_sdf is the input ligand structure for UD2 engine. By now, contains no Hydrogen atoms
    mol_ref = Chem.SDMolSupplier(str(fp_sdf), removeHs=noH)[0]
    for key in mol_ref.GetPropNames():
        mol_ref.ClearProp(key)

    ligand_name = list(json_res.keys())[0]
    assert len(ligand_name) > 0, "ligand_name not found!"
    if new_name is None:
        new_name = ligand_name

    # create a writer
    writer = Chem.SDWriter(fp_res_sdf)

    for idx, pose in enumerate(json_res[ligand_name]):
        mol_res = Chem.Mol(mol_ref)  # new copy for each pose
        mol_res.SetProp("_Name", f"{new_name}_pose_{idx}")
        conf = mol_res.GetConformer()

        coords_res = np.array(pose["coords"]).reshape(-1, 3)
        for i in range(conf.GetNumAtoms()):
            conf.SetAtomPosition(i, coords_res[i])

        # add energy property (assume energy value in pose dictionary)
        if "energy" in pose:
            # convert energy list to space-separated string
            energy_str = " ".join([f"{e:.3f}" for e in pose["energy"]])
            mol_res.SetProp("energy", energy_str)

        # output conf to sdf file
        writer.write(mol_res)

        # rmsd = rdMolAlign.CalcRMS(mol_ref, mol_res)
        # list_rmsd.append(rmsd)
    writer.close()

