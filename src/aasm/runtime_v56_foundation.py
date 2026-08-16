from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine


class AASMEngine(SolverProvenanceRuntimeMixin, SolverOutcomeV2RuntimeMixin, V55FoundationEngine):
    """v0.56 family runtime: truthful solver outcomes plus governed execution provenance over v0.55."""


__all__ = ["AASMEngine"]
