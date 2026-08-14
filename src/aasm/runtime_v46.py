from .runtime_v45 import AASMEngine as V45Engine
from ._runtime_v46_advanced import AdvancedOptimizationRuntimeMixin


class AASMEngine(AdvancedOptimizationRuntimeMixin, V45Engine):
    """AASM v0.46 runtime: v0.45 plus advanced native solver control/search artifacts."""

    pass


__all__ = ["AASMEngine"]
