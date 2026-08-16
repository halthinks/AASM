from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .external_machine_runtime import ExternalMachineRuntimeMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine
from .state_authority_runtime import StateAuthorityRuntimeMixin


class AASMEngine(
    ExternalMachineRuntimeMixin,
    StateAuthorityRuntimeMixin,
    SolverProvenanceRuntimeMixin,
    SolverOutcomeV2RuntimeMixin,
    V55FoundationEngine,
):
    """Active v0.56 development runtime with truthful solver evidence and governed external-state correlation."""


__all__ = ["AASMEngine"]
