"""
Configuration module for Uni-Dock Benchmarks.

This module contains:
- BenchmarkConfig: A class to encapsulate runtime configuration
- Constants: File format definitions (FMT_UD1, FMT_UD2) and default values
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkConfig:
    """
    Runtime configuration for benchmark tests.
    All runtime settings should be passed through this config object
    instead of using global variables.
    """
    version: int = 1  # Uni-Dock version: 1 or 2
    device_id: int = 0  # GPU device ID
    seed: int = 10000  # Random seed
    bin: Optional[str] = None  # Binary path (default based on version)
    nowater: bool = False  # Use receptor without water
    type: str = "molecular_docking"  # Benchmark type: molecular_docking or virtual_screening
    rootdir: Optional[str] = None  # Root directory of the data
    savedir: Optional[str] = None  # Saved directory for the results
    
    # Derived properties
    @property
    def fn_suffix(self) -> str:
        """File suffix based on water option."""
        return "" if self.nowater else "_water"
    
    @property
    def default_bin(self) -> str:
        """Default binary path based on version."""
        return "ud1" if self.version == 1 else "ud2"
    
    @property
    def binary(self) -> str:
        """Get binary path (user-provided or default)."""
        return self.bin if self.bin is not None else self.default_bin
    
    @property
    def search_mode_list(self) -> list:
        """Search mode list based on version."""
        return ["detail"] if self.version == 1 else ["free"]
    
    def print_config(self) -> str:
        """
        打印 BenchmarkConfig 对象的所有参数。
        
        Returns:
            格式化的参数字符串
        """
        lines = [
            "=" * 60,
            "Benchmark Configuration:",
            "=" * 60,
            f"  Version:           {self.version}",
            f"  Type:               {self.type}",
            f"  Binary:             {self.binary}",
            f"  Device ID:          {self.device_id}",
            f"  Seed:               {self.seed}",
            f"  No Water:           {self.nowater}",
            f"  Root Directory:     {self.rootdir}",
            f"  Save Directory:     {self.savedir}",
            f"  Search Mode List:   {self.search_mode_list}",
            f"  File Suffix:        {self.fn_suffix}",
            "=" * 60
        ]
        return "\n".join(lines)


# Constants - file format definitions (read-only)
CSV_NAME = "res.csv"  # default result file name

FMT_UD1 = { # format of path relative to "pdb_id/"
    "Astex": {
        "sdf": "unidock1_protein{0}/ligand_prepared_torsion_tree.sdf", # {id_pdb}
        "pdb": "unidock1_protein{0}/receptor.pdbqt",
        "out": "ligand_prepared_torsion_tree_out.sdf" # {id_pdb}
    },
    "CASF2016": {
        "sdf": "unidock1_protein{0}/ligand_prepared_torsion_tree.sdf", # {id_pdb}
        "pdb": "unidock1_protein{0}/receptor.pdbqt",
        "out": "ligand_prepared_torsion_tree_out.sdf" # {id_pdb}
    },
    "PoseBuster": {
        "sdf": "unidock1_protein{0}/ligand_prepared_torsion_tree.sdf", # {id_pdb}
        "pdb": "unidock1_protein{0}/receptor.pdbqt",
        "out": "ligand_prepared_torsion_tree_out.sdf" # {id_pdb}
    },
    "D4": {
        "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
        "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
        "pdb": "unidock1_protein/receptor.pdbqt", 
    },
    "GBA": {
        "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
        "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
        "pdb": "unidock1_protein/receptor.pdbqt", 
    },
    "NSP3": {
        "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
        "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
        "pdb": "unidock1_protein/receptor.pdbqt", 
    },
    "PPARG": {
        "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
        "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
        "pdb": "unidock1_protein/receptor.pdbqt", 
    },
    "sigma2": {
        "active": "unidock1_protein/actives_prepared_torsion_tree.sdf",
        "inactive": "unidock1_protein/inactives_prepared_torsion_tree.sdf",
        "pdb": "unidock1_protein/receptor.pdbqt", 
    }
}

FMT_UD2 = { # format of path relative to "unidock2"
    "Astex": {
        "sdf": "ligand_prepared.sdf", # {id_pdb}
        "json": "unidock2_protein{0}/{1}_unidock2.json", # {id_pdb}
        "out": "{1}_unidock2_1.json" # {id_pdb}
    },
    "CASF2016": {
        "sdf": "ligand_prepared.sdf", # {id_pdb}
        "json": "unidock2_protein{0}/{1}_unidock2.json", # {id_pdb}
        "out": "{1}_unidock2_1.json" # {id_pdb}
    },  
    "PoseBuster": {
        "sdf": "ligand_prepared.sdf", # {id_pdb}
        "json": "unidock2_protein{0}/{1}_unidock2.json", # {id_pdb}
        "out": "{1}_unidock2_1.json" # {id_pdb}
    },
    "D4": {
        "active": "unidock2_protein/actives_unidock2.json",
        "inactive": "unidock2_protein/inactives_unidock2.json",
    },
    "GBA": {
        "active": "unidock2_protein/actives_unidock2.json",
        "inactive": "unidock2_protein/inactives_unidock2.json",
    },
    "NSP3": {
        "active": "unidock2_protein/actives_unidock2.json",
        "inactive": "unidock2_protein/inactives_unidock2.json",
    },
    "PPARG": {
        "active": "unidock2_protein/actives_unidock2.json",
        "inactive": "unidock2_protein/inactives_unidock2.json",
    },
    "sigma2": {
        "active": "unidock2_protein/actives_unidock2.json",
        "inactive": "unidock2_protein/inactives_unidock2.json",
    }
}