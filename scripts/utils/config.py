"""
Configuration module for Uni-Dock Benchmarks.

This module contains:
- BenchmarkConfig: A class to encapsulate runtime configuration
- Constants: Default values shared across the benchmark suite
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
            f"  File Suffix:        {self.fn_suffix}",
            "=" * 60
        ]
        return "\n".join(lines)


# Constants
CSV_NAME = "res.csv"  # default result file name
