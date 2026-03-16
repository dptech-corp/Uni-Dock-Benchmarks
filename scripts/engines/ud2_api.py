"""Uni-Dock V2 API engine implementation.

Uses unidock_engine DockingPipeline (in-process) instead of the Uni-Dock2
CLI binary.  Requires the unidock_engine package (e.g. from Uni-Dock2 /
conda env ud2pub).
"""

import contextlib
import json
import os
import time
import copy
import traceback
import yaml
from typing import List, Tuple

from engines.base import DockingEngine
from utils.calc_rmsd import calc_rmsd, tran_json_to_sdf
from utils.myio import read_json


_EXCLUDE_KEYS = ("receptor", "score")

# Reuse same path conventions as Uni-Dock V2 (binary).
_UD2_DOCK_FMT = {
    "sdf": "ligand_prepared.sdf",
    "json": "unidock2_protein{0}/{1}_unidock2.json",
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
    """Uni-Dock V2 engine via DockingPipeline API (no CLI binary)."""

    def __init__(self, config):
        super().__init__(config)
        self._ud2_base_config = self._load_ud2_config()

    def _load_ud2_config(self) -> dict:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fp_ud2_yaml = os.path.join(script_dir, "ud2.yaml")
        with open(fp_ud2_yaml, "r") as f:
            return yaml.safe_load(f)

    def _pipeline_kwargs(self, data_center: dict, search_mode: str,
                         center_format: str = "molecular_docking") -> dict:
        """Build kwargs dict for DockingPipeline constructor."""
        cfg = copy.deepcopy(self._ud2_base_config)
        adv = cfg.get("Advanced", {})
        sett = cfg.get("Settings", {})

        if center_format == "molecular_docking":
            cx, cy, cz = float(data_center["X"]), float(data_center["Y"]), float(data_center["Z"])
            sx, sy, sz = 30.0, 30.0, 30.0
        else:
            cx = float(data_center["center_x"])
            cy = float(data_center["center_y"])
            cz = float(data_center["center_z"])
            sx = float(data_center["size_x"])
            sy = float(data_center["size_y"])
            sz = float(data_center["size_z"])

        hw = cfg.get("Hardware", {})
        return dict(
            center_x=cx, center_y=cy, center_z=cz,
            size_x=sx, size_y=sy, size_z=sz,
            task=sett.get("task", "screen"),
            search_mode=search_mode,
            exhaustiveness=adv.get("exhaustiveness", 512),
            randomize=adv.get("randomize", True),
            mc_steps=adv.get("mc_steps", 40),
            opt_steps=adv.get("opt_steps", -1),
            refine_steps=adv.get("refine_steps", 1),
            num_pose=adv.get("num_pose", 10),
            rmsd_limit=adv.get("rmsd_limit", 1.0),
            energy_range=adv.get("energy_range", 10.0),
            seed=self.config.seed,
            use_tor_lib=adv.get("tor_lib", False),
            constraint_docking=False,
            gpu_device_id=self.config.device_id,
            max_gpu_mem=hw.get("max_gpu_memory", 0),
        )

    def _run_pipeline(self, fp_json: str, output_dir: str,
                      data_center: dict, search_mode: str,
                      center_format: str = "molecular_docking") -> None:
        """Load an integrated JSON and run DockingPipeline."""
        from unidock_engine.api.python import pipeline

        with open(fp_json, "r") as f:
            data = json.load(f)

        receptor_info = data.get("receptor", [])
        ligands_info = {k: v for k, v in data.items() if k not in _EXCLUDE_KEYS}

        os.makedirs(output_dir, exist_ok=True)
        kw = self._pipeline_kwargs(data_center, search_mode, center_format)

        dp = pipeline.DockingPipeline(output_dir=output_dir,
                                      **{k: v for k, v in kw.items()})
        dp.set_receptor(receptor_info)
        dp.add_ligands(ligands_info)
        dp.run()

    @property
    def search_modes(self) -> List[str]:
        return ["free"]

    # --- Molecular Docking ---

    def build_dock_command(self, dp_data_id, dataset, id_pdb, data_center,
                           dp_res_case, search_mode):
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
        """Run one docking case via DockingPipeline API."""
        fp_json = os.path.join(
            dp_data_id,
            FMT_UD2[dataset]["json"].format(self.config.fn_suffix, id_pdb),
        )
        os.makedirs(dp_res_case, exist_ok=True)
        fp_log = os.path.join(dp_res_case, "ud2.log")
        start = time.perf_counter()
        try:
            with open(fp_log, "w") as log_f:
                with contextlib.redirect_stdout(log_f), contextlib.redirect_stderr(log_f):
                    self._run_pipeline(
                        fp_json, dp_res_case, data_center, search_mode,
                        center_format="molecular_docking",
                    )
            return 0, time.perf_counter() - start
        except Exception:
            cost = time.perf_counter() - start
            with open(fp_log, "a") as log_f:
                log_f.write(traceback.format_exc())
            return -1, cost

    def compute_dock_rmsd(self, dp_data_id, dataset, id_pdb, dp_res_case):
        fp_ligand_ref = os.path.join(dp_data_id, f"{id_pdb}_ligand.sdf")
        fp_ligand_input = os.path.join(dp_data_id, FMT_UD2[dataset]["sdf"])

        # Pipeline writes result JSON(s) into dp_res_case; find the first one.
        res_jsons = sorted(
            f for f in os.listdir(dp_res_case) if f.endswith(".json")
        )
        if not res_jsons:
            raise FileNotFoundError(f"No result JSON found in {dp_res_case}")
        fp_res_json = os.path.join(dp_res_case, res_jsons[0])

        fp_res_sdf = os.path.join(dp_res_case, "ud2_1.sdf")
        tran_json_to_sdf(fp_res_json, fp_ligand_input, fp_res_sdf)
        return calc_rmsd(fp_ligand_ref, fp_res_sdf)

    # --- Virtual Screening ---

    def build_screen_commands(self, dp_data, dataset, data_center,
                              dp_res_case, search_mode):
        return []

    def execute_screen_cases(
        self,
        dp_data: str,
        dataset: str,
        data_center: dict,
        dp_res_case: str,
        search_mode: str,
    ) -> Tuple[int, float]:
        """Run active + inactive screening via DockingPipeline API."""
        total_cost = 0.0
        for name in ("inactive", "active"):
            fp_json = os.path.join(dp_data, FMT_UD2[dataset][name])
            out_dir = os.path.join(dp_res_case, name)
            os.makedirs(out_dir, exist_ok=True)
            fp_log = os.path.join(out_dir, "ud2.log")
            start = time.perf_counter()
            try:
                with open(fp_log, "w") as log_f:
                    with contextlib.redirect_stdout(log_f), contextlib.redirect_stderr(log_f):
                        self._run_pipeline(
                            fp_json, out_dir, data_center, search_mode,
                            center_format="virtual_screening",
                        )
            except Exception:
                with open(fp_log, "a") as log_f:
                    log_f.write(traceback.format_exc())
                total_cost += time.perf_counter() - start
                return -1, total_cost
            total_cost += time.perf_counter() - start
        return 0, total_cost

    def parse_screen_affinity(self, dp_res_case) -> List[Tuple[str, float, int]]:
        results = []
        for active, name in enumerate(["inactive", "active"]):
            dp = os.path.join(dp_res_case, name)
            for fn in sorted(f for f in os.listdir(dp) if f.endswith(".json")):
                fp_json = os.path.join(dp, fn)
                data = read_json(fp_json)
                for ligand_name, poses in data.items():
                    results.append((ligand_name, poses[0]["energy"][0], active))
        return results
