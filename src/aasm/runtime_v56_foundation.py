from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .external_machine_postcondition_execution_correlation import MachinePostconditionExecutionCorrelationMixin
from .external_machine_postcondition_runtime import MachinePostconditionRuntimeMixin
from .external_machine_runtime import ExternalMachineRuntimeMixin
from .external_machine_transition_runtime import MachineTransitionRuntimeMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine
from .state_authority_runtime import StateAuthorityRuntimeMixin


class AASMEngine(
    MachinePostconditionExecutionCorrelationMixin,
    MachinePostconditionRuntimeMixin,
    MachineTransitionRuntimeMixin,
    ExternalMachineRuntimeMixin,
    StateAuthorityRuntimeMixin,
    SolverProvenanceRuntimeMixin,
    SolverOutcomeV2RuntimeMixin,
    V55FoundationEngine,
):
    """Active v0.56 development runtime with governed external-state transition and postcondition verification."""


__all__ = ["AASMEngine"]
