# Uni-Dock-Benchmarks

The Uni-Dock-Benchmarks repository provides a comprehensive collection of datasets for benchmarking the Uni-Dock docking system's performance and accuracy.
The datasets include prepared structures and input files for both Uni-Dock V1 and V2 for benchmarks.

## Data

**Important Note**
Some benchmark data files exceed GitHub's file size limits and are stored in cloud storage. To download the complete benchmark data directory, please run the following command in your terminal:
```sh
./getData.sh
```

The benchmark data is categorized into two primary sections: `molecular_docking`and `virtual_screening`.

### Molecular Docking Benchmarks

Under the `molecular_docking` directory, you will find several well-known benchmark datasets:

- `Astex`: [Hartshorn, M. J., Verdonk, M. L., Chessari, G., Brewerton, S. C., Mooij, W. T., Mortenson, P. N., & Murray, C. W. (2007). Diverse, high-quality test set for the validation of protein− ligand docking performance. Journal of medicinal chemistry, 50(4), 726-741.](https://pubs.acs.org/doi/full/10.1021/jm061277y)
- `CASF2016`: [Su, M., Yang, Q., Du, Y., Feng, G., Liu, Z., Li, Y., & Wang, R. (2018). Comparative assessment of scoring functions: the CASF-2016 update. Journal of chemical information and modeling, 59(2), 895-913.](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.8b00545)
- `PoseBuster`: [Buttenschoen, M., Morris, G. M., & Deane, C. M. (2024). PoseBusters: AI-based docking methods fail to generate physically valid poses or generalise to novel sequences. Chemical Science.](https://pubs.rsc.org/en/content/articlehtml/2024/sc/d3sc04185a)

We performed the following preparation steps for the proteins and ligands in the datasets.

- After obtaining the protein structures from the RCSB database based on the PDB code, we retained the crystal waters that affect the binding mode and completed missing protein side chains and lost hydrogen atoms.
- For ligands, we searched the RCSB database for the isomer SMILES corresponding to the PDB code and determined the correct protonation state according to the receptor pocket environment. Then, we generated 3D conformations for each ligand.

After excluding systems for covalent ligand bindings, problematic binding mechanisms and those with large natural products or polypeptide ligands, **69** systems from `Astex`, **271** systems from `CASF-2016` and **396** systems from `PoseBuster` were used as benchmarks.

The correctness of protein side chain structure and hydrogen bond networks have crucial impact on ligand docking, and hence the structure preparation for both protein and ligand determines the difficultness of producing correct ligand docking poses. We use our internal tools to prepare the initial structures of receptor and ligands so that we can obtain better docking results. In addition, we also integrated the open-sourced version of structure preparation algorithms for Uni-Dock V2 into the unified protocol in the Uni-Dock V2 github repository.

We prepare the receptor structure in two versions, protein with co-crystallized water version and protein only version, to test the overall effect of the presence of water on ligand docking experiments.

The directory structure for each dataset is as follows:

```sh
<DataSetName>
├── <PDB_ID>
│   ├── <PDB_ID>_ligand.sdf                    # Ligand co-crystal structure processed in SDF format
│   ├── <PDB_ID>_protein_water_cleaned.pdb     # Prepared receptor structure with protein and crystallized water in PDB format
│   ├── <PDB_ID>_protein_cleaned.pdb           # Prepared receptor structure with only protein in PDB format
│   ├── ligand_prepared.sdf                    # Reprepared ligand 3D conformation used in docking test in SDF format
│   ├── unidock1_protein                       # Folder for input files of Uni-Dock V1, with protein only in the receptor structure
│   │   ├── ligand_prepared_torsion_tree.sdf   # Prepared ligand structure with torsion tree information used in Uni-Dock V1 input in SDF format
│   │   └── receptor.pdbqt                     # Prepared receptor structure used in Uni-Dock V1 input in PDBQT format
│   ├── unidock1_protein_water                 # Folder for input files of Uni-Dock V1, with protein and water in the receptor structure
│   │   ├── ligand_prepared_torsion_tree.sdf   # Prepared ligand structure with torsion tree information used in Uni-Dock V1 input in SDF format
│   │   └── receptor.pdbqt                     # Prepared receptor structure used in Uni-Dock V1 input in PDBQT format
│   ├── unidock2_protein                       # Folder for input files of Uni-Dock V2, with protein only in the receptor structure
│   │   ├── <PDB_ID>_unidock2.json             # Integrated JSON input file for Uni-Dock V2 docking engine
│   │   └── receptor_parameterized.dms         # Prepared and parameterized receptor structure in DMS format
│   └── unidock2_protein_water                 # Folder for input files of Uni-Dock V2, with protein and water in the receptor structure
│       ├── <PDB_ID>_unidock2.json             # Integrated JSON input file for Uni-Dock V2 docking engine
│       └── receptor_parameterized.dms         # Prepared and parameterized receptor structure in DMS format
└── pdb_center.csv                             # CSV file recording the protein pocket center with respect to the <PDB_ID> for each system
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
├── docking_grid.json                         # JSON file recording the protein pocket center and the box sizes
├── <PDB_ID>_receptor.pdb                     # Original unprocessed receptor structure in PDB format
├── <PDB_ID>_protein_cleaned.pdb              # Prepared receptor structure with only protein in PDB format
├── actives_cleaned.sdf                       # Preprocessed and cleaned active molecules in SDF format
├── actives.sdf                               # Active molecules in SDF format
├── inactives_cleaned.sdf                     # Preprocessed and cleaned inactive molecules in SDF format
├── inactives.sdf                             # Inactive molecules in SDF format
├── unidock1_protein                          # Folder for input files of Uni-Dock V1, with protein only in the receptor structure
│   ├── actives_prepared_torsion_tree.sdf     # Prepared active molecule structure with torsion tree information used in Uni-Dock V1 input in SDF format
│   ├── inactives_prepared_torsion_tree.sdf   # Prepared inactive molecule structure with torsion tree information used in Uni-Dock V1 input in SDF format
│   └── receptor.pdbqt                        # Prepared receptor structure used in Uni-Dock V1 input in PDBQT format
└── unidock2_protein                          # Folder for input files of Uni-Dock V2, with protein only in the receptor structure
    ├── actives_unidock2.json                 # Integrated JSON input file of active molecules for Uni-Dock V2 docking engine
    ├── inactives_unidock2.json               # Integrated JSON input file of inactive molecules for Uni-Dock V2 docking engine
    └── receptor_parameterized.dms            # Prepared and parameterized receptor structure in DMS format
```


---

## Quick Start

### 1. Install Python dependencies

```sh
pip install tqdm rdkit numpy pandas pyyaml matplotlib
```

### 2. Download benchmark data

```sh
./getData.sh
```

### 3. Run benchmarks

Generate a config from the built-in template, edit it, then run:

```sh
./run.sh dump_config my_bench.yaml   # creates my_bench.yaml from template
vim my_bench.yaml                    # set engine, datasets, seeds, GPUs, etc.
./run.sh my_bench.yaml               # launch benchmarks
```

The YAML config controls engine version/binary, benchmark type, datasets, output directory,
and per-run seed + GPU assignment. Runs on the same GPU execute sequentially for accurate
timing; runs on different GPUs execute in parallel.

<details>
<summary>Legacy CLI modes</summary>

```sh
# Single run (foreground)
./run.sh single --savedir results/dock_v2 --bin ud2 --version 2 \
  --type molecular_docking --device 0 --seed 123

# Batch run (3 seeds × 3 GPUs, background)
./run.sh batch results/dock_v2 0 1 2 --bin ud2 --version 2 --type molecular_docking
```

</details>

### 4. Analyze results

```sh
./analyze.sh --runs results/dock_v2_1 results/dock_v2_2 results/dock_v2_3 \
  --output analysis/dock --name dock_v2

# Merge tables only, skip plots
./analyze.sh --runs results/screen_v2 --output analysis/screen --name screen_v2 --no-plot
```

Outputs: `<name>_metrics_merged.csv`, `<name>_res_merged.csv`, and optional PNG plots.

