from .runtime_v48 import AASMEngine as V48Engine
from ._runtime_v49_rc import SemanticSolverRCRuntimeMixin


class AASMEngine(SemanticSolverRCRuntimeMixin, V48Engine):
    """AASM v0.49 RC runtime: v0.48 semantics plus release-candidate assurance surfaces."""

    pass


__all__ = ["AASMEngine"]
