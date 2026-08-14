from .runtime_v44 import AASMEngine as V44Engine
from ._runtime_v45_convex import ConvexOptimizationRuntimeMixin


class AASMEngine(ConvexOptimizationRuntimeMixin, V44Engine):
    """AASM v0.45 runtime: v0.44 portfolio plus governed CVXPY and PuLP compatibility."""

    pass


__all__ = ["AASMEngine"]
