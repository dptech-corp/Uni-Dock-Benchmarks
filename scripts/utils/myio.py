import json
import yaml

def read_json(fp):
    with open(fp, "r") as f:
        data = json.load(f)
    return data

def write_json(data:dict, fp):
    with open(fp, "w") as f:
        json.dump(data, f)

def read_yaml(fp):
    with open(fp, "r") as f:
        data = yaml.safe_load(f)
    return data

def write_yaml(data:dict, fp):
    with open(fp, "w") as f:
        yaml.safe_dump(data, f)

def read_text(fp):
    with open(fp, "r") as f:
        data = f.read()
    return data

def write_text(ss:str, fp):
    with open(fp, "w") as f:
        f.write(ss)

def read_sdf_coords(fp:str, multi=False, removeHs=False):
    from rdkit import Chem
    if multi:
        dict_coords = dict()
        mols = Chem.SDMolSupplier(fp, removeHs=removeHs)
        for mol in mols:
            name = mol.GetProp("_Name")
            conf = mol.GetConformer()
            dict_coords[name] = conf.GetPositions()
        return dict_coords
    else:
        mol = Chem.SDMolSupplier(fp, removeHs=removeHs)[0]
        conf = mol.GetConformer()
        return conf.GetPositions()

def read_pdb_coords(fp: str):
    from rdkit import Chem
    import numpy as np
    
    # not sanitize to avoid parsing error
    mol = Chem.MolFromPDBFile(fp, sanitize=False)
    if not mol:
        raise ValueError("Failed to read PDB File!")
    
    conformer = mol.GetConformer()
    coords = []
    
    # iterate over all atoms
    for atom in mol.GetAtoms():
        pos = conformer.GetAtomPosition(atom.GetIdx())
        coords.append([pos.x, pos.y, pos.z])
    
    return np.array(coords)
