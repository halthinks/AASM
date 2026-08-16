from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .effect_capability_revocation_guard import EffectCapabilityRevocationGuardMixin
from .effect_capability_runtime import EffectCapabilityRuntimeMixin
from .external_machine_postcondition_execution_correlation import MachinePostconditionExecutionCorrelationMixin
from .external_machine_postcondition_runtime import MachinePostconditionRuntimeMixin
from .external_machine_runtime import ExternalMachineRuntimeMixin
from .external_machine_transition_runtime import MachineTransitionRuntimeMixin
from .physical_authority_runtime import PhysicalAuthorityRuntimeMixin
from .physical_control_fencing_runtime import PhysicalControlFencingRuntimeMixin
from .physical_preemption_recovery_guard import PhysicalPreemptionRecoveryGuardMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine
from .state_authority_runtime import StateAuthorityRuntimeMixin


class AASMEngine(
    PhysicalPreemptionRecoveryGuardMixin,
    PhysicalControlFencingRuntimeMixin,
    EffectCapabilityRevocationGuardMixin,
    EffectCapabilityRuntimeMixin,
    PhysicalAuthorityRuntimeMixin,
    MachinePostconditionExecutionCorrelationMixin,
    MachinePostconditionRuntimeMixin,
    MachineTransitionRuntimeMixin,
    ExternalMachineRuntimeMixin,
    StateAuthorityRuntimeMixin,
    SolverProvenanceRuntimeMixin,
    SolverOutcomeV2RuntimeMixin,
    V55FoundationEngine,
):
    """Active v0.56 development runtime with governed external reality and PR-3 physical-control foundations."""


__all__ = ["AASMEngine"]
