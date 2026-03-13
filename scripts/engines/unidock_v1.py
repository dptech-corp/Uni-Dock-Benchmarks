"""Uni-Dock V1 engine implementation."""

import os
import re
from typing import List, Tuple

from engines.base import DockingEngine
from utils.calc_rmsd import calc_rmsd
from utils.myio import read_text, write_text

_ENERGY_RE = re.compile(r'ENERGY=\s*([-\d.eE+]+)')


# Default file-path templates for Uni-Dock V1.
# Molecular docking: {0} = fn_suffix (water flag), {1} = pdb_id.
# Virtual screening: fixed paths (no per-PDB variation).
# New datasets following the same convention need no code change — just add the
# dataset directory under data/.
_UD1_DOCK_FMT = {
    "sdf": "unidock1_protein{0}/ligand_prepared_torsion_tree.sdf",
    "pdb": "unidock1_protein{0}/receptor.pdbqt",
    "out": "ligand_prepared_torsion_tree_out.sdf",
}

_UD1_SCREEN_FMT = {
    "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
    "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
    "pdb": "unidock1_protein/receptor.pdbqt",
}

_DOCK_DATASETS = ("Astex", "CASF2016", "PoseBuster")
_SCREEN_DATASETS = ("D4", "GBA", "NSP3", "PPARG", "sigma2")

FMT_UD1 = {d: _UD1_DOCK_FMT for d in _DOCK_DATASETS}
FMT_UD1.update({d: _UD1_SCREEN_FMT for d in _SCREEN_DATASETS})


class UniDockV1Engine(DockingEngine):
    """Uni-Dock V1 engine implementation."""

    @property
    def search_modes(self) -> List[str]:
        return ["detail"]

    # --- Molecular Docking ---

    def build_dock_command(self, dp_data_id, dataset, id_pdb, data_center,
                           dp_res_case, search_mode):
        fp_ligand = os.path.join(
            dp_data_id,
            FMT_UD1[dataset]["sdf"].format(self.config.fn_suffix, id_pdb),
        )
        fp_receptor = os.path.join(
            dp_data_id,
            FMT_UD1[dataset]["pdb"].format(self.config.fn_suffix, id_pdb),
        )
        return [
            self.config.binary,
            "--receptor", str(fp_receptor),
            "--gpu_batch", str(fp_ligand),
            "--center_x", f"{data_center['X']:.1f}",
            "--center_y", f"{data_center['Y']:.1f}",
            "--center_z", f"{data_center['Z']:.1f}",
            "--size_x", f"{30.0:.1f}",
            "--size_y", f"{30.0:.1f}",
            "--size_z", f"{30.0:.1f}",
            "--dir", str(dp_res_case),
            "--keep_nonpolar_H",
            "--device_id", str(self.config.device_id),
            "--cpu", "32",
            "--seed", str(self.config.seed),
            "--search_mode", search_mode,
        ]

    def compute_dock_rmsd(self, dp_data_id, dataset, id_pdb, dp_res_case):
        fp_ligand_ref = os.path.join(dp_data_id, f"{id_pdb}_ligand.sdf")
        fp_ligand_out = os.path.join(
            dp_res_case,
            FMT_UD1[dataset]["out"],
        )
        return calc_rmsd(fp_ligand_ref, fp_ligand_out)

    # --- Virtual Screening ---

    def build_screen_commands(self, dp_data, dataset, data_center,
                              dp_res_case, search_mode):
        fp_pdb = os.path.join(dp_data, FMT_UD1[dataset]["pdb"])
        commands = []

        for name in ["inactive", "active"]:
            fp_sdf = os.path.join(dp_data, FMT_UD1[dataset][name])
            dp = os.path.join(dp_res_case, name)
            os.makedirs(dp, exist_ok=True)

            dp_split = os.path.join(dp, "split")
            os.makedirs(dp_split, exist_ok=True)
            fp_index = os.path.join(dp, "index.txt")

            ss_index = ""
            ss_sdf = read_text(fp_sdf).strip().strip("\n").rstrip("$$$$")
            for ss in ss_sdf.split("$$$$"):
                lig_name = ss.strip().strip("\n").split("\n")[0]
                fp_lig = os.path.join(dp_split, f"{lig_name}.sdf")
                write_text(ss.strip().strip("\n") + "\n\n$$$$", fp_lig)
                ss_index += fp_lig + " "
            write_text(ss_index, fp_index)

            commands.append([
                self.config.binary,
                "--receptor", str(fp_pdb),
                "--ligand_index", str(fp_index),
                "--center_x", f"{data_center['center_x']:.1f}",
                "--center_y", f"{data_center['center_y']:.1f}",
                "--center_z", f"{data_center['center_z']:.1f}",
                "--size_x", f"{data_center['size_x']:.1f}",
                "--size_y", f"{data_center['size_y']:.1f}",
                "--size_z", f"{data_center['size_z']:.1f}",
                "--dir", str(dp),
                "--keep_nonpolar_H",
                "--scoring", "vina",
                "--num_modes", "10",
                "--refine_step", "5",
                "--device_id", str(self.config.device_id),
                "--cpu", "32",
                "--search_mode", search_mode,
            ])

        return commands

    def parse_screen_affinity(self, dp_res_case) -> List[Tuple[str, float, int]]:
        results = []
        for active, name in enumerate(["inactive", "active"]):
            dp = os.path.join(dp_res_case, name)
            for fn in [i for i in os.listdir(dp) if i.endswith(".sdf")]:
                fp_sdf = os.path.join(dp, fn)
                ss = read_text(fp_sdf)
                stem, _ = os.path.splitext(fn)
                ligand_name = stem.removesuffix("_out")
                first_block = ss.split("$$$$")[0]
                match = _ENERGY_RE.search(first_block)
                energy = float(match.group(1))
                results.append((ligand_name, energy, active))
        return results
