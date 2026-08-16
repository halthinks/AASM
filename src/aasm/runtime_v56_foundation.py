from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine
from .state_authority_runtime import StateAuthorityRuntimeMixin


class AASMEngine(
    StateAuthorityRuntimeMixin,
    SolverProvenanceRuntimeMixin,
    SolverOutcomeV2RuntimeMixin,
    V55FoundationEngine,
):
    """Active v0.56 development runtime over v0.55 with truthful solver evidence and governed state authority."""


__all__ = ["AASMEngine"]
