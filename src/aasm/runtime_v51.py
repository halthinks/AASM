from __future__ import annotations

from ._runtime_v51_pools import SolutionPoolRuntimeMixin
from .runtime_v50 import AASMEngine as V50Engine


class AASMEngine(SolutionPoolRuntimeMixin, V50Engine):
    """v0.51 governed solution pools layered over the v0.50 proof runtime."""
    pass


__all__ = ["AASMEngine"]
