from __future__ import annotations

from typing import Any

from ._safety_envelope_common import (
    SAFETY_ENVELOPE_CONTRACT_ID, SAFETY_ENVELOPE_CONTRACT_VERSION,
    HYBRID_STATE_CONTRACT_ID, HYBRID_STATE_CONTRACT_VERSION,
    SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID, SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION,
    SAFETY_ENVELOPE_HYBRID_STATE_STABILITY, HYBRID_OBSERVATION_STATUSES,
    CONSTRAINT_RELATIONS, SAFETY_ENVELOPE_ASSESSMENT_STATUSES,
)
from ._safety_envelope_records import SafetyEnvelopeConstraint, SafetyModeEnvelope, SafetyEnvelope
from ._hybrid_state_records import HybridQuantityObservation, HybridState
from ._safety_envelope_assessment_records import SafetyConstraintAssessment, SafetyEnvelopeAssessment
from ._safety_envelope_validation import (
    bind_safety_constraint, observe_hybrid_quantity, unknown_hybrid_quantity,
    validate_safety_envelope, validate_hybrid_state,
)
from ._safety_envelope_evaluation import assess_safety_envelope

def safety_envelope_hybrid_state_contract() -> dict[str, Any]:
    return {
        "safety_envelope_contract_id": SAFETY_ENVELOPE_CONTRACT_ID,
        "safety_envelope_contract_version": SAFETY_ENVELOPE_CONTRACT_VERSION,
        "hybrid_state_contract_id": HYBRID_STATE_CONTRACT_ID,
        "hybrid_state_contract_version": HYBRID_STATE_CONTRACT_VERSION,
        "assessment_contract_id": SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID,
        "assessment_contract_version": SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION,
        "stability": SAFETY_ENVELOPE_HYBRID_STATE_STABILITY,
        "continuous_quantity_semantics": "EXACT_EXISTING_AASM_QUANTITY_V1_REFERENCE_ONLY_NO_SECOND_NUMERIC_OR_UNIT_SYSTEM",
        "hard_safety_legality": "EXACT_EXISTING_AASM_RULE_V1_HARD_FLOOR_SAFETY_INVARIANT_REFERENCE_ONLY_NO_SECOND_HARD_FLOOR_SYSTEM",
        "hybrid_state_role": "REVISION_BOUND_OBSERVATION_OF_DISCRETE_MODE_AND_CONTINUOUS_QUANTITIES_ONLY",
        "discrete_mode_role": "OBSERVED_LABEL_ONLY_NOT_CURRENT_OPERATIONAL_MODE_OR_MODE_ACTIVATION",
        "external_dynamics": "EXTERNAL_SOLVER_OR_EVIDENCE_REFERENCES_ONLY",
        "ode_solver": "NONE",
        "physics_solver": "NONE",
        "dynamics_integration": "NONE",
        "trajectory_prediction": "NONE",
        "controller_synthesis": "NONE",
        "allowed_region": "INTERVAL_QUANTITY_WITHOUT_TOLERANCE_OR_QUANTIZATION",
        "observed_support": "EXACT_INTERVAL_OR_MEASURED_QUANTITY_WITH_EXACT_TOLERANCE_EXPANSION",
        "non_exact_quantization": "UNSUPPORTED_FAIL_CLOSED_TO_INDETERMINATE",
        "uncertain_boundary_overlap": "INDETERMINATE_NOT_SAFE",
        "unknown_or_missing_observation": "INDETERMINATE_NOT_SAFE",
        "uncovered_mode": "MODE_UNCOVERED_NOT_SAFE",
        "assessment_statuses": list(SAFETY_ENVELOPE_ASSESSMENT_STATUSES),
        "constraint_relations": list(CONSTRAINT_RELATIONS),
        "assessment_is_authorization": False,
        "assessment_is_fact_authority": False,
        "assessment_is_physical_state_authority": False,
        "assessment_is_empirical_safety_proof": False,
        "assessment_activates_mode": False,
        "assessment_dispatches_effect": False,
        "assessment_accepts_artifact": False,
        "parallel_safety_state_machine": "NONE",
        "parallel_operational_mode_store": "NONE",
        "parallel_rule_system": "NONE",
        "parallel_quantity_system": "NONE",
        "parallel_evidence_store": "NONE",
        "parallel_authority_evaluator": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "SAFETY_ENVELOPE_CONTRACT_ID",
    "SAFETY_ENVELOPE_CONTRACT_VERSION",
    "HYBRID_STATE_CONTRACT_ID",
    "HYBRID_STATE_CONTRACT_VERSION",
    "SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID",
    "SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION",
    "SAFETY_ENVELOPE_HYBRID_STATE_STABILITY",
    "HYBRID_OBSERVATION_STATUSES",
    "CONSTRAINT_RELATIONS",
    "SAFETY_ENVELOPE_ASSESSMENT_STATUSES",
    "SafetyEnvelopeConstraint",
    "SafetyModeEnvelope",
    "SafetyEnvelope",
    "HybridQuantityObservation",
    "HybridState",
    "SafetyConstraintAssessment",
    "SafetyEnvelopeAssessment",
    "bind_safety_constraint",
    "observe_hybrid_quantity",
    "unknown_hybrid_quantity",
    "validate_safety_envelope",
    "validate_hybrid_state",
    "assess_safety_envelope",
    "safety_envelope_hybrid_state_contract",
]
