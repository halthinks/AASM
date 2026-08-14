from __future__ import annotations

from ._runtime_v50_proof import ProofClaimRuntimeMixin
from .runtime_v49 import AASMEngine as V49Engine


class AASMEngine(ProofClaimRuntimeMixin, V49Engine):
    """v0.50 proof-carrying solver claims layered over the v0.49 RC runtime."""
    pass


__all__ = ["AASMEngine"]
