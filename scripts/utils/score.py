"""
Backward-compatible import shim for legacy scoring helpers.
"""

from utils.trash import ef_score, read_ud1_score

__all__ = ["read_ud1_score", "ef_score"]