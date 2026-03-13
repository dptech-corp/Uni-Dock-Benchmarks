"""Uni-Dock V2 API engine implementation.

Uses unidock_processing.UnidockProtocolRunner (in-process) instead of the
Uni-Dock2 CLI binary. Requires the unidock_processing package (e.g. from
Uni-Dock2 / conda env ud2pub).
"""

import os
import time
import copy
import yaml
from typing import List, Tuple

from engines.base import DockingEngine
from utils.calc_rmsd import calc_rmsd
from utils.myio import read_json, write_yaml


# Reuse same path conventions as Uni-Dock V2 (binary).
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


class UniDockV2APIEngine(DockingEngine):
    """Uni-Dock V2 engine via unidock_processing API (no CLI binary)."""

    def __init__(self, config):
        super().__init__(config)
        self._ud2_base_config = self._load_ud2_config()

    def _load_ud2_config(self) -> dict:
        """Load default ud2.yaml template for protocol kwargs."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fp_ud2_yaml = os.path.join(script_dir, "ud2.yaml")
        with open(fp_ud2_yaml, "r") as f:
            return yaml.safe_load(f)

    def _protocol_kwargs(self, data_center: dict, search_mode: str,
                        center_format: str = "molecular_docking") -> dict:
        """Build kwargs for UnidockProtocolRunner from config + center."""
        cfg = copy.deepcopy(self._ud2_base_config)
        adv = cfg.get("Advanced", {})
        hw = cfg.get("Hardware", {})
        sett = cfg.get("Settings", {})

        if center_format == "molecular_docking":
            center = (float(data_center["X"]), float(data_center["Y"]), float(data_center["Z"]))
            box_size = (30.0, 30.0, 30.0)
        else:
            center = (
                float(data_center["center_x"]),
                float(data_center["center_y"]),
                float(data_center["center_z"]),
            )
            box_size = (
                float(data_center["size_x"]),
                float(data_center["size_y"]),
                float(data_center["size_z"]),
            )

        return {
            "target_center": center,
            "box_size": box_size,
            "gpu_device_id": self.config.device_id,
            "seed": self.config.seed,
            "search_mode": search_mode,
            "exhaustiveness": adv.get("exhaustiveness", 512),
            "randomize": adv.get("randomize", True),
            "mc_steps": adv.get("mc_steps", 40),
            "opt_steps": adv.get("opt_steps", -1),
            "refine_steps": adv.get("refine_steps", 5),
            "num_pose": adv.get("num_pose", 10),
            "rmsd_limit": adv.get("rmsd_limit", 1.0),
            "energy_range": adv.get("energy_range", 10.0),
            "use_tor_lib": adv.get("tor_lib", False),
            "task": sett.get("task", "screen"),
        }

    @property
    def search_modes(self) -> List[str]:
        return ["free"]

    # --- Molecular Docking (API path) ---

    def build_dock_command(self, dp_data_id, dataset, id_pdb, data_center,
                           dp_res_case, search_mode):
        # Not used when execute_dock_case is present; return placeholder.
        return []

    def execute_dock_case(
        self,
        dp_data_id: str,
        dataset: str,
        id_pdb: str,
        data_center: dict,
        dp_res_case: str,
        search_mode: str,
    ) -> Tuple[int, float]:
        """Run one docking case via UnidockProtocolRunner. Returns (returncode, cost_time)."""
        from unidock_processing.unidocktools.unidock_protocol_runner import (
            UnidockProtocolRunner,
        )

        fp_receptor_json = os.path.join(
            dp_data_id,
            FMT_UD2[dataset]["json"].format(self.config.fn_suffix, id_pdb),
        )
        fp_ligand_sdf = os.path.join(dp_data_id, FMT_UD2[dataset]["sdf"])
        fp_out_sdf = os.path.join(dp_res_case, "ud2_1.sdf")

        kwargs = self._protocol_kwargs(data_center, search_mode, "molecular_docking")
        kwargs["receptor_file_name"] = fp_receptor_json
        kwargs["ligand_sdf_file_name_list"] = [fp_ligand_sdf]
        kwargs["working_dir_name"] = dp_res_case
        kwargs["docking_pose_sdf_file_name"] = fp_out_sdf

        os.makedirs(dp_res_case, exist_ok=True)
        start = time.perf_counter()
        try:
            runner = UnidockProtocolRunner(**kwargs)
            runner.run_unidock_protocol()
            cost = time.perf_counter() - start
            return 0, cost
        except Exception:
            cost = time.perf_counter() - start
            return -1, cost

    def compute_dock_rmsd(self, dp_data_id, dataset, id_pdb, dp_res_case):
        # API writes SDF directly; no json->sdf conversion.
        fp_ligand_ref = os.path.join(dp_data_id, f"{id_pdb}_ligand.sdf")
        fp_res_sdf = os.path.join(dp_res_case, "ud2_1.sdf")
        return calc_rmsd(fp_ligand_ref, fp_res_sdf)

    # --- Virtual Screening (API path) ---

    def _build_ud2_command(self, fp_json, data_center, dp_res_case,
                           search_mode, *, use_log=True,
                           center_format="molecular_docking") -> list:
        """Build CLI command for UD2 (used for screening when binary is set)."""
        config_ud2 = copy.deepcopy(self._ud2_base_config)
        config_ud2["Advanced"]["seed"] = self.config.seed
        config_ud2["Settings"]["search_mode"] = search_mode
        if center_format == "molecular_docking":
            config_ud2["Settings"]["center_x"] = data_center["X"]
            config_ud2["Settings"]["center_y"] = data_center["Y"]
            config_ud2["Settings"]["center_z"] = data_center["Z"]
            config_ud2["Settings"]["size_x"] = 30.0
            config_ud2["Settings"]["size_y"] = 30.0
            config_ud2["Settings"]["size_z"] = 30.0
        else:
            config_ud2["Settings"]["center_x"] = data_center["center_x"]
            config_ud2["Settings"]["center_y"] = data_center["center_y"]
            config_ud2["Settings"]["center_z"] = data_center["center_z"]
            config_ud2["Settings"]["size_x"] = data_center["size_x"]
            config_ud2["Settings"]["size_y"] = data_center["size_y"]
            config_ud2["Settings"]["size_z"] = data_center["size_z"]
        config_ud2["Inputs"]["json"] = fp_json
        config_ud2["Outputs"]["dir"] = dp_res_case
        config_ud2["Hardware"]["gpu_device_id"] = self.config.device_id
        fp_ud2_config = os.path.join(dp_res_case, "ud2.yaml")
        write_yaml(config_ud2, fp_ud2_config)
        if use_log:
            return [self.config.binary, "--log",
                    os.path.join(dp_res_case, "ud2.log"), fp_ud2_config]
        return [self.config.binary, fp_ud2_config]

    def build_screen_commands(self, dp_data, dataset, data_center,
                              dp_res_case, search_mode):
        # Screening uses CLI binary (same as V2); requires engine.binary to be set.
        commands = []
        for name in ["inactive", "active"]:
            fp_json = os.path.join(dp_data, FMT_UD2[dataset][name])
            dp = os.path.join(dp_res_case, name)
            os.makedirs(dp, exist_ok=True)
            commands.append(self._build_ud2_command(
                fp_json, data_center, dp, search_mode,
                use_log=False, center_format="virtual_screening",
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
