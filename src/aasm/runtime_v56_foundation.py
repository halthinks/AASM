from __future__ import annotations

from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine


class AASMEngine(SolverOutcomeV2RuntimeMixin, V55FoundationEngine):
    """Development-only v0.56 truthful solver-evidence foundation over v0.55 candidate semantics."""


__all__ = ["AASMEngine"]
