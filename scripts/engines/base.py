"""Abstract base class for Uni-Dock docking engines."""

from abc import ABC, abstractmethod
from typing import List, Tuple

from utils.config import BenchmarkConfig


class DockingEngine(ABC):
    """
    Abstract base class for Uni-Dock docking engines.

    Each engine version (V1, V2, ...) implements this interface
    to encapsulate version-specific file formats, command generation,
    and result parsing.
    """

    def __init__(self, config: BenchmarkConfig):
        self.config = config

    @property
    @abstractmethod
    def search_modes(self) -> List[str]:
        """Available search modes for this engine."""
        ...

    # --- Molecular Docking ---

    @abstractmethod
    def build_dock_command(
        self,
        dp_data_id: str,
        dataset: str,
        id_pdb: str,
        data_center: dict,
        dp_res_case: str,
        search_mode: str,
    ) -> list:
        """Generate the CLI command for a single molecular docking case."""
        ...

    @abstractmethod
    def compute_dock_rmsd(
        self,
        dp_data_id: str,
        dataset: str,
        id_pdb: str,
        dp_res_case: str,
    ) -> List[float]:
        """Compute RMSD values between docking result and reference ligand."""
        ...

    # --- Virtual Screening ---

    @abstractmethod
    def build_screen_commands(
        self,
        dp_data: str,
        dataset: str,
        data_center: dict,
        dp_res_case: str,
        search_mode: str,
    ) -> List[list]:
        """
        Generate CLI commands for a virtual screening run.

        Returns a list of commands (each command is a list of strings),
        since screening may require separate runs for actives and inactives.
        """
        ...

    @abstractmethod
    def parse_screen_affinity(
        self, dp_res_case: str
    ) -> List[Tuple[str, float, int]]:
        """
        Parse affinity scores from screening results.

        Returns list of (ligand_name, affinity_energy, active_flag) tuples,
        where active_flag is 0 for inactive and 1 for active.
        """
        ...
