"""Engine abstraction layer for Uni-Dock benchmarks."""

from engines.base import DockingEngine
from engines.unidock_v1 import UniDockV1Engine
from engines.unidock_v2 import UniDockV2Engine
from utils.config import BenchmarkConfig


def create_engine(config: BenchmarkConfig) -> DockingEngine:
    """Factory function to create the appropriate engine based on config version."""
    engines = {
        1: UniDockV1Engine,
        2: UniDockV2Engine,
    }
    engine_cls = engines.get(config.version)
    if engine_cls is None:
        raise ValueError(
            f"Unsupported Uni-Dock version: {config.version}. "
            f"Supported versions: {list(engines.keys())}"
        )
    return engine_cls(config)
