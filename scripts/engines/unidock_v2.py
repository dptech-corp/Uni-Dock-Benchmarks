"""Uni-Dock V2 engine implementation."""

import os
import copy
import yaml
from typing import List, Tuple

from engines.base import DockingEngine
from utils.calc_rmsd import calc_rmsd, tran_json_to_sdf
from utils.myio import read_json, write_yaml


# Default file-path templates for Uni-Dock V2.
# Molecular docking: {0} = fn_suffix (water flag), {1} = pdb_id.
# Virtual screening: fixed paths.
# New datasets following the same convention need no code change — just add the
# dataset directory under data/.
_UD2_DOCK_FMT = {
    "sdf": "ligand_prepared.sdf",
    "json": "unidock2_protein{0}/{1}_unidock2.json",
    "out": "{1}_unidock2_1.json",
}

_UD2_SCREEN_FMT = {
    "active": "unidock2_protein/actives_unidock2.json",
    "inactive": "unidock2_protein/inactives_unidock2.json",
}

_DOCK_DATASETS = ("Astex", "CASF2016", "PoseBuster")
_SCREEN_DATASETS = ("D4", "GBA", "NSP3", "PPARG", "sigma2")

FMT_UD2 = {d: _UD2_DOCK_FMT for d in _DOCK_DATASETS}
FMT_UD2.update({d: _UD2_SCREEN_FMT for d in _SCREEN_DATASETS})


class UniDockV2Engine(DockingEngine):
    """Uni-Dock V2 engine implementation."""

    def __init__(self, config):
        super().__init__(config)
        self._ud2_base_config = self._load_ud2_config()

    def _load_ud2_config(self) -> dict:
        """Load the default ud2.yaml configuration template."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fp_ud2_yaml = os.path.join(script_dir, "ud2.yaml")
        with open(fp_ud2_yaml, "r") as f:
            return yaml.safe_load(f)

    def _build_ud2_command(self, fp_json, data_center, dp_res_case,
                           search_mode, *, use_log=True,
                           center_format="molecular_docking") -> list:
        """Build command for UD2 by writing a per-case YAML config."""
        config_ud2 = copy.deepcopy(self._ud2_base_config)

        config_ud2["Advanced"]["seed"] = self.config.seed
        config_ud2["Settings"]["search_mode"] = search_mode

        for key, value in self.config.runner_args.items():
            for section in ("Advanced", "Settings", "Hardware"):
                if key in config_ud2.get(section, {}):
                    config_ud2[section][key] = value
                    break

        if center_format == "molecular_docking":
            config_ud2["Settings"]["center_x"] = data_center['X']
            config_ud2["Settings"]["center_y"] = data_center['Y']
            config_ud2["Settings"]["center_z"] = data_center['Z']
            config_ud2["Settings"]["size_x"] = 30.0
            config_ud2["Settings"]["size_y"] = 30.0
            config_ud2["Settings"]["size_z"] = 30.0
        else:  # virtual_screening
            config_ud2["Settings"]["center_x"] = data_center['center_x']
            config_ud2["Settings"]["center_y"] = data_center['center_y']
            config_ud2["Settings"]["center_z"] = data_center['center_z']
            config_ud2["Settings"]["size_x"] = data_center['size_x']
            config_ud2["Settings"]["size_y"] = data_center['size_y']
            config_ud2["Settings"]["size_z"] = data_center['size_z']

        config_ud2["Inputs"]["json"] = fp_json
        config_ud2["Outputs"]["dir"] = dp_res_case
        config_ud2["Hardware"]["gpu_device_id"] = self.config.device_id

        fp_ud2_config = os.path.join(dp_res_case, "ud2.yaml")
        write_yaml(config_ud2, fp_ud2_config)

        if use_log:
            return [self.config.binary, "--log",
                    os.path.join(dp_res_case, "ud2.log"), fp_ud2_config]
        else:
            return [self.config.binary, fp_ud2_config]

    @property
    def search_modes(self) -> List[str]:
        return ["free"]

    # --- Molecular Docking ---

    def build_dock_command(self, dp_data_id, dataset, id_pdb, data_center,
                           dp_res_case, search_mode):
        fp_json = os.path.join(
            dp_data_id,
            FMT_UD2[dataset]["json"].format(self.config.fn_suffix, id_pdb),
        )
        return self._build_ud2_command(
            fp_json, data_center, dp_res_case, search_mode,
            use_log=True, center_format="molecular_docking",
        )

    def compute_dock_rmsd(self, dp_data_id, dataset, id_pdb, dp_res_case):
        fp_ligand_ref = os.path.join(dp_data_id, f"{id_pdb}_ligand.sdf")
        fp_ligand_input = os.path.join(
            dp_data_id,
            FMT_UD2[dataset]["sdf"],
        )
        fp_res_json = os.path.join(
            dp_res_case,
            FMT_UD2[dataset]["out"].format(self.config.fn_suffix, id_pdb),
        )
        fp_res_sdf = os.path.join(dp_res_case, "ud2_1.sdf")
        tran_json_to_sdf(fp_res_json, fp_ligand_input, fp_res_sdf)
        return calc_rmsd(fp_ligand_ref, fp_res_sdf)

    # --- Virtual Screening ---

    def build_screen_commands(self, dp_data, dataset, data_center,
                              dp_res_case, search_mode):
        commands = []
        for name in ["inactive", "active"]:
            fp_json = os.path.join(dp_data, FMT_UD2[dataset][name])
            dp = os.path.join(dp_res_case, name)
            os.makedirs(dp, exist_ok=True)
            commands.append(self._build_ud2_command(
                fp_json, data_center, dp, search_mode,
                use_log=True, center_format="virtual_screening",
            ))
        return commands

    def parse_screen_affinity(self, dp_res_case) -> List[Tuple[str, float, int]]:
        results = []
        for active, name in enumerate(["inactive", "active"]):
            dp = os.path.join(dp_res_case, name)
            for fn in [i for i in os.listdir(dp) if i.endswith(".json")]:
                fp_json = os.path.join(dp, fn)
                data = read_json(fp_json)
                for ligand_name, poses in data.items():
                    results.append((ligand_name, poses[0]["energy"][0], active))
        return results
