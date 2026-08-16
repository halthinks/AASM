from __future__ import annotations

import aasm
from aasm import public_v55, public_v56


def test_v56_is_active_v0561_and_v55_remains_frozen_parent():
    report = public_v56.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v56.__version__ == "0.56.1"
    assert public_v56.PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"
    assert public_v56.PUBLIC_API_CONTRACT["contract_version"] == "0.32.6"
    assert public_v56.PUBLIC_API_CONTRACT["runtime_version"] == "0.56.1"
    assert public_v55.__version__ == "0.55.0"
    assert aasm.__version__ == "0.56.1"
    assert aasm.AASMEngine is public_v56.AASMEngine
    assert public_v56.AASMEngine is not public_v55.AASMEngine


def test_v56_active_engine_exposes_external_reality_and_physical_authority_foundations():
    for method in (
        "solver_outcome_v2_runtime_contract_report", "record_solver_outcome_v2", "solver_outcome_v2_report",
        "solver_provenance_runtime_contract_report", "register_solver_execution_profile", "record_solver_runtime_provenance",
        "record_convex_solver_runtime_provenance", "evaluate_solver_runtime_profile", "solver_provenance_report",
        "state_authority_contract_report", "register_fact_authority", "revoke_fact_authority",
        "record_state_claim", "state_claim_report", "state_authority_report",
        "external_machine_contract_report", "register_machine_binding", "record_machine_state_observation",
        "machine_binding_report", "machine_state_observation_report", "external_machine_report",
        "machine_transition_contract_report", "propose_machine_transition", "machine_transition_report",
        "machine_transitions_report", "machine_postcondition_contract_report",
        "verify_machine_transition_postconditions", "machine_postcondition_verification_report",
        "machine_postconditions_report", "physical_authority_contract_report",
        "register_authority_domain", "grant_authority_lease", "revoke_authority_lease",
        "authority_domain_report", "authority_lease_report", "physical_authority_report",
    ):
        assert callable(getattr(public_v56.AASMEngine, method))
        assert method in public_v56.SUPPORTED_ENGINE_METHODS


def test_v56_release_preserves_truthful_external_reality_and_physical_authority_boundaries():
    contract = public_v56.public_api_contract()
    outcome = contract["solver_outcome_v2"]
    assert outcome["authoritative_detailed_status"] == "normalized_status"
    assert outcome["legacy_projection"] == "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED"
    assert outcome["incumbent_admission"] == "NONEMPTY_ASSIGNMENT_MUST_PASS_AASM_INDEPENDENT_MODEL_VALIDATION"
    assert outcome["provider_status_map"]["substring_inference"] == "FORBIDDEN"
    assert outcome["runtime"]["parallel_result_table"] == "NONE"

    provenance = contract["solver_provenance"]
    assert provenance["runtime_provenance_contract_id"] == "aasm.solver.runtime-provenance.v1"
    assert provenance["effective_options"] == "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED"
    assert provenance["worker_thread_counts"] == "FIRST_CLASS_EXPLICIT_OR_UNKNOWN"
    assert provenance["runtime"]["parallel_provenance_table"] == "NONE"
    assert provenance["runtime"]["provenance_grants_reproducibility"] is False
    assert provenance["truth_authority"] == "NONE"
    assert provenance["policy_authority"] == "NONE"
    assert provenance["interrupted_provenance_v2"] == "DORMANT_NON_AUTHORITATIVE_NOT_EXPOSED"

    state_authority = contract["state_authority"]
    assert state_authority["claim_kinds"] == ["DESIRED", "PREDICTED", "OBSERVED", "AUTHORITATIVE"]
    assert state_authority["observed"] == "EMPIRICAL_EVIDENCE_ONLY_NOT_AUTHORITATIVE_BY_EXISTENCE_OR_AGREEMENT"
    assert state_authority["authoritative"] == "EXPLICIT_MATCHING_FACT_AUTHORITY_AND_SOURCE_CLAIM_REQUIRED"
    assert state_authority["aggregation_grants_authority"] is False
    assert state_authority["fact_authority_grants_effect_authority"] is False
    assert state_authority["runtime"]["parallel_truth_table"] == "NONE"
    assert state_authority["runtime"]["machine_state_mutation"] == "NONE"
    assert state_authority["runtime"]["effect_authority"] == "NONE"

    external = contract["external_machine"]
    assert external["binding_role"] == "REFERENCE_AND_CORRELATION_ONLY_NOT_EXTERNAL_STATE_COPY"
    assert external["binding_grants_fact_authority"] is False
    assert external["binding_grants_effect_authority"] is False
    assert external["capability_reference_grants_authority"] is False
    assert external["external_state_table"] == "NONE"
    assert external["runtime"]["effect_dispatch"] == "NONE"
    assert external["runtime"]["machine_state_mutation"] == "NONE"

    transition = contract["machine_transition"]
    assert transition["effect_proposal"] == "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY"
    assert transition["effect_authorization"] == "EXISTING_AASM_AUTHORIZE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT"
    assert transition["effect_dispatch"] == "EXISTING_AASM_EXECUTE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT"
    assert transition["parallel_dispatcher"] == "NONE"
    assert transition["parallel_effect_store"] == "NONE"
    assert transition["command_success_is_achievement"] is False
    assert transition["runtime"]["effect_proposal_path"] == "EXISTING_AASM_PROPOSE_EFFECT_ONLY"
    assert transition["runtime"]["effect_dispatch"] == "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT"
    assert transition["runtime"]["transition_status_store"] == "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD"

    post = contract["machine_postcondition"]
    assert post["effect_status_requirement"] == "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED"
    assert post["unknown_effect"] == "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION"
    assert post["observation_correlation"] == "PR2A_MACHINE_STATE_OBSERVATION_CORRELATION_ID_MUST_EQUAL_EXISTING_EFFECT_EXECUTION_ID"
    assert post["effect_success_is_achievement"] is False
    assert post["verification_mints_fact_authority"] is False
    assert post["verification_mints_state_claim"] is False
    assert post["verification_mutates_effect_outcome"] is False
    assert post["verification_grants_effect_authority"] is False
    assert post["parallel_truth_table"] == "NONE"
    assert post["parallel_effect_lifecycle"] == "NONE"
    assert post["freshness_semantics"] == "NOT_YET_CLAIMED_PR4"
    assert post["calibration_semantics"] == "NOT_YET_CLAIMED_PR4"

    physical = contract["physical_authority"]
    assert physical["domain_role"] == "BOUNDED_EFFECT_AUTHORITY_NAMESPACE_NOT_AUTHORITY_GRANT"
    assert physical["lease_role"] == "EXCLUSIVE_TIME_BOUNDED_DOMAIN_HOLDER_NOT_EFFECT_PERMISSION_BY_EXISTENCE"
    assert physical["lease_exclusivity"] == "AT_MOST_ONE_ACTIVE_LEASE_PER_DOMAIN"
    assert physical["authority_epoch"] == "STRICTLY_MONOTONIC_PER_DOMAIN"
    assert physical["resource_availability_grants_authority"] is False
    assert physical["fact_authority_grants_effect_authority"] is False
    assert physical["domain_existence_grants_effect_authority"] is False
    assert physical["lease_existence_grants_effect_authority"] is False
    assert physical["parallel_authority_evaluator"] == "NONE"
    assert physical["parallel_effect_lifecycle"] == "NONE"
    assert physical["effect_authorization_integration"] == "NOT_YET_PR3H"
    assert physical["bounded_effect_capability"] == "RESERVED_PR3C_PR3D"
    assert physical["semantic_preemption"] == "RESERVED_PR3G"
    assert physical["runtime"]["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert physical["runtime"]["lease_exclusivity"] == "NON_OVERLAPPING_EFFECTIVE_INTERVALS_PER_DOMAIN"
    assert physical["runtime"]["authority_epoch"] == "EXPLICIT_NEXT_MONOTONIC_EPOCH_REQUIRED"
    assert physical["runtime"]["preemptor_reference_grants_authority"] is False
    assert physical["runtime"]["effect_authorization_integration"] == "NONE_PR3A_PR3B_FOUNDATION"
    assert physical["runtime"]["effect_dispatch"] == "NONE"
    assert physical["runtime"]["machine_state_mutation"] == "NONE"
    assert physical["runtime"]["parallel_authority_evaluator"] == "NONE"
    assert physical["runtime"]["parallel_effect_lifecycle"] == "NONE"


def test_v56_release_import_registry_contains_external_reality_and_physical_authority_contracts():
    for name in (
        "ProviderTermination", "SolverEvidenceGrade", "LegacyStatusProjection", "SolverOutcomeV2",
        "ProviderStatusRule", "ProviderStatusMap", "ProviderStatusMapping", "normalize_optimization_result_v2",
        "project_v2_to_legacy_status", "map_provider_status", "SolverExecutionProfile", "SolverRuntimeProvenance",
        "SolverProfileEvaluation", "SolverExecutionObservation", "build_solver_runtime_provenance",
        "evaluate_solver_execution_profile", "solver_provenance_contract", "solver_provenance_runtime_contract",
        "FactAuthority", "StateClaim", "STATE_CLAIM_KINDS", "state_authority_contract",
        "state_authority_runtime_contract", "STATE_AUTHORITY_CAPABILITIES",
        "MachineBinding", "MachineStateObservation", "external_machine_contract",
        "external_machine_runtime_contract", "EXTERNAL_MACHINE_CAPABILITIES",
        "MachineTransitionIntent", "machine_transition_contract", "machine_transition_runtime_contract",
        "MACHINE_TRANSITION_CAPABILITIES", "MachinePostconditionVerification",
        "machine_postcondition_verification_contract", "machine_postcondition_runtime_contract",
        "MACHINE_POSTCONDITION_CAPABILITIES", "POSTCONDITION_VERDICTS",
        "AuthorityDomain", "AuthorityLease", "physical_authority_contract",
        "physical_authority_runtime_contract", "PHYSICAL_AUTHORITY_CAPABILITIES",
    ):
        assert hasattr(public_v56, name)
        assert name in public_v56.SUPPORTED_PUBLIC_IMPORTS
