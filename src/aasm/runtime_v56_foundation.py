from __future__ import annotations

from ._runtime_v56_provenance import SolverProvenanceRuntimeMixin
from ._runtime_v56_solver_outcome import SolverOutcomeV2RuntimeMixin
from .artifact_lineage_runtime import ArtifactLineageRuntimeMixin
from .calibration_runtime import CalibrationRuntimeMixin
from .effect_capability_revocation_guard import EffectCapabilityRevocationGuardMixin
from .effect_capability_runtime import EffectCapabilityRuntimeMixin
from .entity_evolution_runtime import EntityEvolutionRuntimeMixin
from .event_causality_runtime import EventCausalityRuntimeMixin
from .execution_environment_runtime import ExecutionEnvironmentRuntimeMixin
from .external_machine_postcondition_execution_correlation import MachinePostconditionExecutionCorrelationMixin
from .external_machine_postcondition_runtime import MachinePostconditionRuntimeMixin
from .external_machine_runtime import ExternalMachineRuntimeMixin
from .external_machine_transition_runtime import MachineTransitionRuntimeMixin
from .observation_freshness_runtime import ObservationFreshnessRuntimeMixin
from .observation_processing_runtime import ObservationProcessingRuntimeMixin
from .physical_authority_runtime import PhysicalAuthorityRuntimeMixin
from .physical_control_fencing_runtime import PhysicalControlFencingRuntimeMixin
from .physical_effect_integration_boundary import PhysicalEffectIntegrationBoundaryMixin
from .physical_identity_runtime import PhysicalIdentityRuntimeMixin
from .physical_preemption_recovery_guard import PhysicalPreemptionRecoveryGuardMixin
from .runtime_v55_foundation import AASMEngine as V55FoundationEngine
from .source_trust_runtime import SourceTrustRuntimeMixin
from .state_authority_runtime import StateAuthorityRuntimeMixin
from .state_conflict_runtime import StateConflictRuntimeMixin


class AASMEngine(
    PhysicalEffectIntegrationBoundaryMixin,
    PhysicalPreemptionRecoveryGuardMixin,
    PhysicalControlFencingRuntimeMixin,
    EffectCapabilityRevocationGuardMixin,
    EffectCapabilityRuntimeMixin,
    PhysicalAuthorityRuntimeMixin,
    MachinePostconditionExecutionCorrelationMixin,
    MachinePostconditionRuntimeMixin,
    MachineTransitionRuntimeMixin,
    ObservationProcessingRuntimeMixin,
    ArtifactLineageRuntimeMixin,
    EntityEvolutionRuntimeMixin,
    ExecutionEnvironmentRuntimeMixin,
    SourceTrustRuntimeMixin,
    CalibrationRuntimeMixin,
    PhysicalIdentityRuntimeMixin,
    ObservationFreshnessRuntimeMixin,
    EventCausalityRuntimeMixin,
    ExternalMachineRuntimeMixin,
    StateConflictRuntimeMixin,
    StateAuthorityRuntimeMixin,
    SolverProvenanceRuntimeMixin,
    SolverOutcomeV2RuntimeMixin,
    V55FoundationEngine,
):
    """Active v0.56 development runtime with governed external reality, bounded effects, S3 observation epistemics, qualified artifact lineage, and candidate entity evolution."""


__all__ = ["AASMEngine"]
