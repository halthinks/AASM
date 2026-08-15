from __future__ import annotations

from ._runtime_v53_solver_learning import SolverLearningRuntimeMixin
from .runtime_v53 import AASMEngine as V53AuthorityEngine


class AASMEngine(SolverLearningRuntimeMixin, V53AuthorityEngine):
    """Experimental full v0.53 composition: scoped authority + solver learning."""


__all__ = ["AASMEngine"]
