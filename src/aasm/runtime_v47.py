from .runtime_v46 import AASMEngine as V46Engine
from ._runtime_v47_sii import SIIGovernanceRuntimeMixin


class AASMEngine(SIIGovernanceRuntimeMixin, V46Engine):
    """AASM v0.47 runtime: v0.46 plus governed SII resource economics."""

    pass


__all__ = ["AASMEngine"]
