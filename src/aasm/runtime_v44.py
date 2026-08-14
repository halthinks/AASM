from .runtime_v41 import AASMEngine as V41Engine
from ._runtime_v44_optimization import OptimizationRuntimeMixin


class AASMEngine(OptimizationRuntimeMixin, V41Engine):
    """AASM v0.44 runtime: v0.41 kernel plus native heterogeneous optimization portfolio."""

    pass


__all__ = ["AASMEngine"]
