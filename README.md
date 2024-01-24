# Uni-Dock-Benchmarks
The Uni-Dock-Benchmarks repository provides a comprehensive collection of datasets for benchmarking the Uni-Dock docking system's performance and accuracy. 

## Data
Benchmark data within the repository is categorized into two primary sections:

- `molecular_docking`
- `virtual_screening`

### Molecular Docking Benchmarks
Under the `molecular_docking` directory, you will find several well-known benchmark datasets:

- `Astex`: [Hartshorn, M. J., Verdonk, M. L., Chessari, G., Brewerton, S. C., Mooij, W. T., Mortenson, P. N., & Murray, C. W. (2007). Diverse, high-quality test set for the validation of protein− ligand docking performance. Journal of medicinal chemistry, 50(4), 726-741.](https://pubs.acs.org/doi/full/10.1021/jm061277y)
- `CASF2016`: [Su, M., Yang, Q., Du, Y., Feng, G., Liu, Z., Li, Y., & Wang, R. (2018). Comparative assessment of scoring functions: the CASF-2016 update. Journal of chemical information and modeling, 59(2), 895-913.](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.8b00545)
- `PoseBuster`: [Buttenschoen, M., Morris, G. M., & Deane, C. M. (2024). PoseBusters: AI-based docking methods fail to generate physically valid poses or generalise to novel sequences. Chemical Science.](https://pubs.rsc.org/en/content/articlehtml/2024/sc/d3sc04185a)

We performed the following preparation steps for the proteins and ligands in the datasets.

- After obtaining the protein structures from the RCSB database based on the PDB code, we retained the crystal waters and cofactors that affect the binding mode and completed missing protein side chains and lost hydrogen atoms. 
- For ligands, we searched the RCSB database for the isomer SMILES corresponding to the PDB code and determined the correct protonation state according to the receptor pocket environment. Then, we generated 3D conformations for each ligand. 

After excluding systems with failed preparation and those with large natural products or polypeptide ligands, **84** systems from `Astex`, **271** systems from `CASF-2016` and **428** systems from `PoseBuster` were used as benchmarks.
  

The directory structure for each dataset is as follows:

```
<DataSetName>
├── <PDB_ID>
│   ├── <PDB_ID>_ligand_ori.sdf  # Original ligand structure in SDF format
│   ├── <PDB_ID>_ligand_prep.sdf # Prepared ligand in SDF format
│   ├── <PDB_ID>_receptor.pdb    # Receptor in PDB format
│   ├── <PDB_ID>_receptor.pdbqt  # Receptor ready for docking in PDBQT format
│   └── docking_grid.json        # Docking box configuration in JSON format
```