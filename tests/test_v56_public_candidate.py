from __future__ import annotations

import aasm
from aasm import public_v55, public_v56


def test_v56_is_active_v0561_and_v55_remains_frozen_parent():
    report = public_v56.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v56.__version__ == "0.56.1"
    assert public_v56.PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"
    assert public_v56.PUBLIC_API_CONTRACT["contract_version"] == "0.32.3"
    assert public_v56.PUBLIC_API_CONTRACT["runtime_version"] == "0.56.1"
    assert public_v55.__version__ == "0.55.0"
    assert aasm.__version__ == "0.56.1"
    assert aasm.AASMEngine is public_v56.AASMEngine
    assert public_v56.AASMEngine is not public_v55.AASMEngine


def test_v56_active_engine_exposes_outcome_provenance_state_authority_and_external_machine_runtime():
    for method in (
        "solver_outcome_v2_runtime_contract_report", "record_solver_outcome_v2", "solver_outcome_v2_report",
        "solver_provenance_runtime_contract_report", "register_solver_execution_profile", "record_solver_runtime_provenance",
        "record_convex_solver_runtime_provenance", "evaluate_solver_runtime_profile", "solver_provenance_report",
        "state_authority_contract_report", "register_fact_authority", "revoke_fact_authority",
        "record_state_claim", "state_claim_report", "state_authority_report",
        "external_machine_contract_report", "register_machine_binding", "record_machine_state_observation",
        "machine_binding_report", "machine_state_observation_report", "external_machine_report",
    ):
        assert callable(getattr(public_v56.AASMEngine, method))
        assert method in public_v56.SUPPORTED_ENGINE_METHODS


def test_v56_release_preserves_truthful_status_provenance_state_authority_and_external_machine_boundaries():
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
    assert external["executor_invocation"] == "NONE_BY_THIS_FOUNDATION"
    assert external["postcondition_achievement_claim"] == "NOT_YET_CLAIMED_PR2C"
    assert external["runtime"]["effect_dispatch"] == "NONE"
    assert external["runtime"]["executor_invocation"] == "NONE"
    assert external["runtime"]["machine_state_mutation"] == "NONE"


def test_v56_release_import_registry_contains_status_provenance_state_authority_and_external_machine_contracts():
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
    ):
        assert hasattr(public_v56, name)
        assert name in public_v56.SUPPORTED_PUBLIC_IMPORTS
