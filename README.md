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

### Virtual Screening Benchmarks

Under the `virtual_screening` directory, you will find several meticulously selected benchmark datasets:

- `D4`: [Lyu, J., Wang, S., Balius, T. E., Singh, I., Levit, A., Moroz, Y. S., ... & Irwin, J. J. (2019). Ultra-large library docking for discovering new chemotypes. Nature, 566(7743), 224-229.](https://www.nature.com/articles/s41586-019-0917-9)
- `GBA`: [Tran-Nguyen, V. K., Jacquemard, C., & Rognan, D. (2020). LIT-PCBA: an unbiased data set for machine learning and virtual screening. Journal of chemical information and modeling, 60(9), 4263-4273.](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.0c00155)
- `NSP3`: [Schuller, M., Correy, G. J., Gahbauer, S., Fearon, D., Wu, T., Díaz, R. E., ... & Ahel, I. (2021). Fragment binding to the Nsp3 macrodomain of SARS-CoV-2 identified through crystallographic screening and computational docking. Science advances, 7(16), eabf8711.](https://www.science.org/doi/full/10.1126/sciadv.abf8711)
- `PPARG`: [Tran-Nguyen, V. K., Jacquemard, C., & Rognan, D. (2020). LIT-PCBA: an unbiased data set for machine learning and virtual screening. Journal of chemical information and modeling, 60(9), 4263-4273.](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.0c00155)
- `sigma2`: [Alon, A., Lyu, J., Braz, J. M., Tummino, T. A., Craik, V., O’Meara, M. J., ... & Kruse, A. C. (2021). Structures of the σ2 receptor enable docking for bioactive ligand discovery. Nature, 600(7890), 759-764.](https://www.nature.com/articles/s41586-021-04175-x)

The following table summarizes the statistics of the datasets:

| Dataset | PDB ID | N_Actives | N_Inactives | N_Total |
|----|----|----|----|----|
| D4 | 5WIU | 226 | 598 | 824 |
| GBA | 5LVX | 286 | 458,205 | 458,491 |
| NSP3 | 5RS7 | 65 | 3,515 | 3,580 |
| PPARG | 5Y2T | 29 | 7,292 | 7,321 |
| sigma2 | 7M94 | 228 | 596 | 824 |

The directory structure for each dataset is as follows:

```
<DataSetName>
├── docking_grid.json          # Docking box configuration in JSON format
├── <PDB_ID>_receptor.pdbqt    # Receptor ready for docking in PDBQT format
├── <PDB_ID>_receptor.pdb      # Receptor in PDB format
├── inactives.sdf              # Inactive molecules in SDF format
└── actives.sdf                # Active molecules in SDF format
```

**ATTENTION**: Since there are too many inactive molecules in `GBA` dataset, the `inactives.sdf` file exceeds the limit of Github, so please download from [GBA-inactives](https://bohrium-api.dp.tech/ds-dl/GBA-inactives-ap7r-v1.zip) and unzip before using it.
