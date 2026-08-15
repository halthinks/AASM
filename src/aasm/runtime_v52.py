from __future__ import annotations

from ._runtime_v52_resources import ResourceGovernanceRuntimeMixin
from .runtime_v51 import AASMEngine as V51Engine


class AASMEngine(ResourceGovernanceRuntimeMixin, V51Engine):
    """Experimental v0.52 resource-governed decision runtime over v0.51."""
    pass


__all__ = ["AASMEngine"]
