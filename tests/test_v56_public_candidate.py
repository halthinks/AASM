from __future__ import annotations

import aasm
from aasm import public_v55, public_v56
import aasm.public_active as public_active


def test_v56_base_is_frozen_and_active_overlay_advances_adoption_only():
    base = public_v56.validate_public_api_contract()
    assert base["valid"] is True, base
    active = aasm.validate_public_api_contract()
    assert active["valid"] is True, active
    assert public_v56.__version__ == "0.56.1"
    assert public_v56.PUBLIC_API_CONTRACT["contract_version"] == "0.32.6"
    assert public_v55.__version__ == "0.55.0"
    assert aasm.__version__ == "0.56.1"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.AASMEngine is public_active.AASMEngine
    assert aasm.AASMEngine is public_v56.AASMEngine
    assert public_v56.AASMEngine is not public_v55.AASMEngine


def test_active_engine_exposes_external_reality_physical_control_and_s3_reality_surface():
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
        "effect_capability_contract_report", "issue_effect_capability", "delegate_effect_capability",
        "revoke_effect_capability", "effect_capability_report", "effect_capabilities_report",
        "physical_control_fencing_contract_report", "validate_effect_capability_use",
        "preempt_authority_lease", "effect_capability_use_report", "authority_preemption_report",
        "physical_control_fencing_report", "physical_effect_integration_contract_report",
        "bind_physical_effect_authority", "physical_effect_binding_report", "physical_effect_integration_report",
        "state_conflict_contract_report", "build_state_conflict", "record_state_conflict",
        "state_conflict_report", "state_conflicts_report",
        "event_causality_contract_report", "record_causal_event", "record_machine_observation_causal_event",
        "record_causal_relation", "causal_event_report", "causal_relation_report", "event_causality_report",
        "observation_freshness_contract_report", "assess_machine_observation_freshness",
        "observation_freshness_assessment_report", "observation_freshness_report",
        "physical_identity_contract_report", "record_physical_identity", "physical_identity_report", "physical_identities_report",
        "calibration_contract_report", "record_calibration", "revoke_calibration", "calibration_report", "calibrations_report",
        "source_trust_contract_report", "record_source_trust", "revoke_source_trust",
        "source_trust_report", "source_trust_assertions_report",
        "execution_environment_contract_report", "record_execution_environment", "bind_machine_observation_environment",
        "execution_environment_report", "execution_environment_binding_report", "execution_environments_report",
        "observation_processing_contract_report", "observation_lifecycle_contract_report", "observation_fusion_contract_report",
        "record_observation_lifecycle", "record_observation_fusion", "record_observation_disposition",
        "observation_lifecycle_record_report", "observation_fusion_record_report", "observation_disposition_report",
        "observation_processing_report",
        "artifact_lineage_runtime_contract_report", "record_artifact_revision",
        "artifact_revision_report", "artifact_lineage_report",
    ):
        assert callable(getattr(aasm.AASMEngine, method)), method
        assert method in aasm.SUPPORTED_ENGINE_METHODS


def test_active_contract_preserves_external_reality_physical_control_and_s3_firewalls():
    contract = aasm.public_api_contract()
    assert contract["contract_version"] == "0.32.20"
    assert contract["parent_contract_version"] == "0.32.19"

    outcome = contract["solver_outcome_v2"]
    assert outcome["authoritative_detailed_status"] == "normalized_status"
    assert outcome["legacy_projection"] == "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED"
    assert outcome["runtime"]["parallel_result_table"] == "NONE"

    state_authority = contract["state_authority"]
    assert state_authority["aggregation_grants_authority"] is False
    assert state_authority["fact_authority_grants_effect_authority"] is False
    assert state_authority["runtime"]["parallel_truth_table"] == "NONE"
    assert state_authority["runtime"]["effect_authority"] == "NONE"

    external = contract["external_machine"]
    assert external["binding_grants_fact_authority"] is False
    assert external["binding_grants_effect_authority"] is False
    assert external["runtime"]["effect_dispatch"] == "NONE"

    transition = contract["machine_transition"]
    assert transition["effect_proposal"] == "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY"
    assert transition["parallel_dispatcher"] == "NONE"
    assert transition["command_success_is_achievement"] is False

    post = contract["machine_postcondition"]
    assert post["effect_success_is_achievement"] is False
    assert post["verification_mints_fact_authority"] is False
    assert post["verification_mints_state_claim"] is False
    assert post["verification_mutates_effect_outcome"] is False
    assert post["verification_grants_effect_authority"] is False
    assert post["parallel_truth_table"] == "NONE"
    assert post["parallel_effect_lifecycle"] == "NONE"

    physical = contract["physical_authority"]
    assert physical["domain_existence_grants_effect_authority"] is False
    assert physical["lease_existence_grants_effect_authority"] is False
    assert physical["parallel_authority_evaluator"] == "NONE"
    assert physical["parallel_effect_lifecycle"] == "NONE"
    assert physical["runtime"]["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert physical["runtime"]["effect_dispatch"] == "NONE"

    capability = contract["effect_capability"]
    assert capability["capability_existence_grants_effect_authority"] is False
    assert capability["dependent_effect_integration"] == "aasm.effect.physical-authority-integration.runtime.v1"
    assert capability["runtime"]["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert capability["runtime"]["non_amplification"] == "OPERATIONS_BOUNDS_VALIDITY_SCOPE_REVISION_EPOCH_AND_DEPTH_FAIL_CLOSED"
    assert capability["runtime"]["effect_dispatch"] == "NONE"

    fencing = contract["physical_control_fencing"]
    assert fencing["use_validation"] == "POINT_IN_TIME_ONLY_REQUIRES_RECHECK_AT_PR3H_EFFECT_BOUNDARIES"
    assert fencing["use_validation_grants_effect_authority"] is False
    assert fencing["preemption_grants_effect_authority"] is False
    assert fencing["parallel_authority_evaluator"] == "NONE"
    assert fencing["parallel_effect_lifecycle"] == "NONE"
    assert fencing["effect_capability_use"]["validation_is_reusable_authorization_token"] is False

    integration = contract["physical_effect_integration"]
    assert integration["binding_existence_grants_effect_authority"] is False
    assert integration["prior_use_validation_is_authorization"] is False
    assert integration["authorization_recheck"] == "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY"
    assert integration["execution_recheck"] == "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY"
    runtime = integration["runtime"]
    assert runtime["effect_authority"] == "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED"
    assert runtime["machine_transition_binding"] == "MANDATORY_BEFORE_AUTHORIZATION_OR_NEW_DISPATCH"
    assert runtime["task_lease"] == "EXISTING_V54_TASKLEASE_UNCHANGED"
    assert runtime["resource_governance"] == "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED"
    assert runtime["ownership"] == "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED"
    assert runtime["unknown_and_reconciliation"] == "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED"
    assert runtime["parallel_authority_evaluator"] == "NONE"
    assert runtime["parallel_effect_store"] == "NONE"
    assert runtime["parallel_effect_lifecycle"] == "NONE"
    assert runtime["parallel_dispatcher"] == "NONE"

    conflict = contract["state_conflict"]
    assert conflict["comparison"] == "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY"
    assert conflict["history"] == "EXPECTATION_AND_ACTUAL_STATE_CLAIMS_REMAIN_UNCHANGED"
    assert conflict["actual_observation_authority"] == "PRESERVE_SOURCE_CLAIM_KIND_NEVER_ELEVATE_OBSERVED_TO_AUTHORITATIVE"
    assert conflict["conflict_grants_fact_authority"] is False
    assert conflict["conflict_grants_effect_authority"] is False
    assert conflict["conflict_mutates_machine_state"] is False
    assert conflict["conflict_mutates_state_claims"] is False
    assert conflict["runtime"]["parallel_truth_table"] == "NONE"

    causal = contract["event_causality"]
    assert causal["local_event_identity"] == "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE"
    assert causal["receipt_order_implies_source_order"] is False
    assert causal["host_wall_clock"] == "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED"
    assert causal["event_identity_grants_authority"] is False
    assert causal["parallel_event_ledger"] == "NONE"
    causal_runtime = causal["runtime"]
    assert causal_runtime["core_aasm_event_log"] == "UNCHANGED_AND_REMAINS_REPLAY_LEDGER"
    assert causal_runtime["same_node_boot_order"] == "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER"
    assert causal_runtime["parallel_event_ledger"] == "NONE"
    assert causal_runtime["parallel_truth_table"] == "NONE"

    freshness = contract["observation_freshness"]
    assert freshness["reference_time"] == "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW"
    assert freshness["receipt_fallback"] == "OPTIONAL_AND_EXPLICITLY_MARKED_WEAKER_AGE_BASIS"
    assert freshness["freshness_grants_fact_authority"] is False
    assert freshness["freshness_grants_effect_authority"] is False
    assert freshness["freshness_elevates_observation_authority"] is False
    assert freshness["freshness_is_universal_admission"] is False
    freshness_runtime = freshness["runtime"]
    assert freshness_runtime["observation_source"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"
    assert freshness_runtime["causal_source"] == "EXACT_DURABLE_CAUSAL_EVENT_ID_AND_FINGERPRINT"
    assert freshness_runtime["reference_time_source"] == "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW"
    assert freshness_runtime["observation_authority_elevation"] == "NONE"
    assert freshness_runtime["universal_admission"] == "NONE"
    assert freshness_runtime["parallel_observation_store"] == "NONE"
    assert freshness_runtime["parallel_truth_table"] == "NONE"

    identity = contract["physical_identity"]
    assert identity["role"] == "EXACT_EXTERNAL_SUBJECT_INSTANCE_CONFIGURATION_REFERENCE_NOT_TRUTH_OR_AUTHORITY_BY_EXISTENCE"
    assert identity["identity_existence_grants_fact_authority"] is False
    assert identity["identity_existence_grants_effect_authority"] is False
    assert identity["identity_existence_grants_source_trust"] is False
    assert identity["host_wall_clock_in_identity"] is False
    assert identity["python_object_identity_in_identity"] is False
    identity_runtime = identity["runtime"]
    assert identity_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert identity_runtime["same_context_divergence"] == "REJECTED_BEFORE_RECORDING_REQUIRE_EXPLICIT_REVISION_CHANGE"
    assert identity_runtime["source_trust"] == "NONE_IDENTITY_IS_ONLY_AN_EXACT_REFERENCE"
    assert identity_runtime["parallel_identity_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert identity_runtime["parallel_truth_table"] == "NONE"

    calibration = contract["calibration"]
    assert calibration["identity_binding"] == "EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT_REQUIRED"
    assert calibration["selection"] == "EXPLICIT_CALIBRATION_ID_NO_HIDDEN_CURRENT_CALIBRATION_POINTER"
    assert calibration["transform_application"] == "NOT_IMPLEMENTED_IN_S3_FOUNDATION"
    assert calibration["calibration_existence_grants_fact_authority"] is False
    assert calibration["calibration_existence_grants_effect_authority"] is False
    assert calibration["calibration_existence_grants_source_trust"] is False
    assert calibration["calibration_mutates_observation"] is False
    calibration_runtime = calibration["runtime"]
    assert calibration_runtime["validity_reference"] == "EXPLICIT_CALLER_NANOSECOND_TIME_ONLY"
    assert calibration_runtime["parallel_calibration_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert calibration_runtime["parallel_truth_table"] == "NONE"

    trust = contract["source_trust"]
    assert trust["role"] == "EXPLICIT_POLICY_INPUT_ABOUT_A_SOURCE_NOT_FACT_AUTHORITY_OR_EFFECT_AUTHORITY"
    assert trust["selection"] == "EXPLICIT_TRUST_ASSERTION_ID_NO_HIDDEN_CURRENT_TRUST_OR_REPUTATION_SCORE"
    assert trust["aggregation"] == "NONE_NO_TRUST_SCORE_NO_VOTING_NO_AUTOMATIC_LATEST_ASSERTION"
    assert trust["trusted_disposition_grants_fact_authority"] is False
    assert trust["trusted_disposition_grants_effect_authority"] is False
    assert trust["trusted_disposition_makes_claim_authoritative"] is False
    assert trust["source_trust_is_universal_admission"] is False
    trust_runtime = trust["runtime"]
    assert trust_runtime["fact_authority"] == "EXISTING_FACT_AUTHORITY_REMAINS_SEPARATE_AND_REQUIRED"
    assert trust_runtime["reputation_score"] == "NONE"
    assert trust_runtime["parallel_authority_evaluator"] == "NONE"
    assert trust_runtime["parallel_trust_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert trust_runtime["parallel_truth_table"] == "NONE"

    environment = contract["execution_environment"]
    assert environment["levels"] == ["MODEL", "SIMULATION", "SIL", "HIL", "BENCH", "CONTROLLED_PHYSICAL", "OPERATIONAL"]
    assert environment["level_ordering"] == "NONE"
    assert environment["higher_level_implies_truth"] is False
    assert environment["higher_level_implies_authority"] is False
    assert environment["automatic_level_upgrade"] is False
    assert environment["simulation_as_physical"] == "REJECT_EXACT_ACCEPTED_LEVELS_ONLY"
    assert environment["cross_environment_evidence_equivalence"] == "NONE_UNLESS_EXPLICIT_EXTERNAL_POLICY"
    assert environment["environment_existence_grants_fact_authority"] is False
    assert environment["environment_existence_grants_effect_authority"] is False
    assert environment["environment_existence_grants_source_trust"] is False
    assert environment["environment_level_is_universal_admission"] is False
    environment_runtime = environment["runtime"]
    assert environment_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_BIND_NOT_ENVIRONMENT_TRUTH"
    assert environment_runtime["level_acceptance"] == "EXACT_ACCEPTED_LEVEL_SET_MEMBERSHIP_NO_ORDINAL_INFERENCE"
    assert environment_runtime["environment_level_authority"] == "NONE"
    assert environment_runtime["physical_identity_source"] == "EXISTING_PHYSICAL_IDENTITY_PROJECTION_ONLY"
    assert environment_runtime["calibration_source"] == "EXISTING_CALIBRATION_PROJECTION_ONLY"
    assert environment_runtime["source_trust_source"] == "EXISTING_SOURCE_TRUST_PROJECTION_ONLY"
    assert environment_runtime["observation_source"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"
    assert environment_runtime["parallel_environment_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert environment_runtime["parallel_observation_store"] == "NONE"
    assert environment_runtime["parallel_truth_table"] == "NONE"
    assert environment_runtime["parallel_authority_evaluator"] == "NONE"

    processing = contract["observation_processing"]
    assert processing["empirical_root"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"
    assert processing["stage_progression"] == "VALIDATED_AT_RUNTIME_NO_SILENT_STAGE_SKIPS"
    assert processing["raw_value"] == "MUST_EQUAL_EXACT_SOURCE_STATE_CLAIM_PORTABLE_VALUE"
    assert processing["current_observation_pointer"] == "NONE"
    assert processing["lifecycle_record_grants_fact_authority"] is False
    assert processing["lifecycle_record_grants_effect_authority"] is False
    assert processing["lifecycle_record_elevates_observation_authority"] is False
    assert processing["validated_stage_is_universal_admission"] is False
    assert processing["parallel_observation_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert processing["parallel_truth_table"] == "NONE"
    fusion = processing["fusion"]
    assert fusion["source_minimum"] == 2
    assert fusion["direct_machine_observation_source"] == "FORBIDDEN_USE_RAW_LIFECYCLE_ROOT_FIRST"
    assert fusion["agreement_semantics"] == "CORROBORATION_ONLY_NEVER_AUTHORITY_OR_TRUTH_BY_VOTE"
    assert fusion["declared_independence_grants_authority"] is False
    assert fusion["validated_by_agreement"] is False
    processing_runtime = processing["runtime"]
    assert processing_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORDING_NOT_OBSERVATION_TRUTH"
    assert processing_runtime["empirical_root"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"
    assert processing_runtime["disposed_source_reuse"] == "FAIL_CLOSED_FOR_NEW_LIFECYCLE_OR_FUSION_RECORDS"
    assert processing_runtime["fact_authority_creation"] == "NONE"
    assert processing_runtime["effect_authority"] == "NONE"
    assert processing_runtime["source_trust_creation"] == "NONE"
    assert processing_runtime["state_claim_creation"] == "NONE"
    assert processing_runtime["source_observation_mutation"] == "NONE"
    assert processing_runtime["current_observation_pointer"] == "NONE"
    assert processing_runtime["parallel_observation_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert processing_runtime["parallel_truth_table"] == "NONE"
    assert processing_runtime["parallel_authority_evaluator"] == "NONE"

    artifact = contract["artifact_lineage"]
    assert artifact["artifact_revision_contract_id"] == "aasm.artifact.revision.v1"
    assert artifact["artifact_revision_contract_version"] == "0.3.0"
    assert artifact["revision_identity"] == "BACKEND_INDEPENDENT_CONTENT_HASH_SEMANTIC_HASH_AND_PROVENANCE_BOUND"
    assert artifact["parent_identity"] == "EXACT_PARENT_REVISION_ID_AND_FINGERPRINT_BINDINGS"
    assert artifact["revision_relation"] == "EXPLICIT_NOT_INFERRED_FROM_RECENCY"
    assert artifact["authority"] == "NONE_GRANTED_BY_ARTIFACT_REVISION"
    assert artifact["truth_authority"] == "EXISTING_AASM_ADMISSION_PATH_ONLY"
    assert artifact["current_artifact_pointer"] == "NONE"
    assert artifact["parallel_artifact_registry"] == "NONE"
    artifact_runtime = artifact["runtime"]
    assert artifact_runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert artifact_runtime["recording_authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert artifact_runtime["evidence_envelope"] == "DETERMINISTIC_ID_OBJECT_ID_OBJECT_FINGERPRINT_AND_CANONICAL_STATEMENT"
    assert artifact_runtime["scope_binding"] == "WORKSPACE_AND_SCOPE_BOUND_TO_DURABLE_REVISION_RECORD"
    assert artifact_runtime["storage_rebinding"] == "APPEND_ONLY_EVIDENCE_BINDING_NOT_REVISION_MUTATION"
    assert artifact_runtime["heads"] == "QUERY_PROJECTION_ONLY_NOT_ACCEPTANCE_OR_AUTHORITY"
    assert artifact_runtime["newest_revision_authority"] == "NONE"
    assert artifact_runtime["artifact_acceptance"] == "NONE_DEFINED_BY_RUNTIME"
    assert artifact_runtime["fact_authority_creation"] == "NONE"
    assert artifact_runtime["source_trust_creation"] == "NONE"
    assert artifact_runtime["effect_authorization"] == "NONE"
    assert artifact_runtime["effect_dispatch"] == "NONE"
    assert artifact_runtime["state_claim_creation"] == "NONE"
    assert artifact_runtime["current_artifact_pointer"] == "NONE"
    assert artifact_runtime["parallel_artifact_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert artifact_runtime["parallel_current_state_store"] == "NONE"
    assert artifact_runtime["runtime_admission"] == "ACTIVE_PUBLIC_ADOPTION"


def test_active_import_registry_contains_pr3_and_s3_reality_contracts():
    for name in (
        "AuthorityDomain", "AuthorityLease", "physical_authority_contract",
        "EffectCapability", "NumericInterval", "effect_capability_contract",
        "effect_capability_runtime_contract", "EFFECT_CAPABILITY_CAPABILITIES",
        "EffectCapabilityUse", "effect_capability_use_contract",
        "AuthorityPreemption", "authority_preemption_contract",
        "physical_control_fencing_runtime_contract", "PHYSICAL_CONTROL_FENCING_CAPABILITIES",
        "PhysicalEffectAuthorityBinding", "physical_effect_authority_binding_contract",
        "physical_effect_integration_runtime_contract", "PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES",
        "StateConflict", "state_conflict_reasons", "state_conflict_contract",
        "state_conflict_runtime_contract", "STATE_CONFLICT_CAPABILITIES",
        "CausalEventIdentity", "CausalRelation", "event_causality_contract",
        "event_causality_runtime_contract", "EVENT_CAUSALITY_CAPABILITIES",
        "ObservationFreshnessAssessment", "assess_freshness", "observation_freshness_contract",
        "observation_freshness_runtime_contract", "OBSERVATION_FRESHNESS_CAPABILITIES",
        "PhysicalIdentity", "physical_identity_contract", "physical_identity_runtime_contract", "PHYSICAL_IDENTITY_CAPABILITIES",
        "CalibrationCertificate", "CalibrationRevocation", "calibration_contract", "calibration_runtime_contract", "CALIBRATION_CAPABILITIES",
        "SourceTrustAssertion", "SourceTrustRevocation", "source_trust_contract", "source_trust_runtime_contract", "SOURCE_TRUST_CAPABILITIES",
        "ExecutionEnvironment", "EnvironmentEvidenceBinding", "environment_level_accepted", "execution_environment_contract",
        "execution_environment_runtime_contract", "EXECUTION_ENVIRONMENT_CAPABILITIES",
        "ObservationSourceRef", "ObservationLifecycleRecord", "ObservationDisposition", "observation_lifecycle_contract",
        "ObservationFusionRecord", "observation_fusion_contract",
        "observation_processing_runtime_contract", "OBSERVATION_PROCESSING_CAPABILITIES",
        "ArtifactRevision", "artifact_lineage_contract", "validate_artifact_revision_transition",
        "ARTIFACT_REVISION_CONTRACT_ID", "ARTIFACT_REVISION_RELATIONS",
        "artifact_lineage_runtime_contract", "project_artifact_lineage_evidence",
        "ARTIFACT_LINEAGE_RUNTIME_CONTRACT_ID", "ARTIFACT_LINEAGE_CAPABILITIES",
    ):
        assert hasattr(aasm, name), name
        assert name in aasm.SUPPORTED_PUBLIC_IMPORTS


def test_active_contract_exposes_s4_quantity_rule_and_projection_foundations_without_runtime_composition():
    contract = aasm.public_api_contract()
    quantity = contract["engineering_quantity"]
    assert quantity["contract_id"] == "aasm.quantity.v1"
    assert quantity["contract_version"] == "0.1.0"
    assert quantity["public_admission"] == "QUALIFIED"
    assert quantity["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert quantity["engine_state_integration"] == "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY"

    rule = contract["engineering_rule"]
    assert rule["contract_id"] == "aasm.rule.v1"
    assert rule["contract_version"] == "0.1.0"
    assert rule["public_admission"] == "QUALIFIED"
    assert rule["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert rule["engine_state_integration"] == "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"
    assert rule["precedence_is_objective_priority"] is False
    assert rule["precedence_authorizes_override"] is False
    assert rule["hard_floor_waiver"] == "FORBIDDEN"
    assert rule["hard_floor_override"] == "FORBIDDEN"
    assert rule["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert rule["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"
    assert rule["parallel_rule_registry"] == "NONE"
    assert rule["current_rule_pointer"] == "NONE"
    assert rule["parallel_constraint_engine"] == "NONE"
    assert rule["parallel_authority_evaluator"] == "NONE"
    assert rule["rule_existence_grants_fact_authority"] is False
    assert rule["rule_existence_grants_effect_authority"] is False
    assert rule["rule_existence_grants_source_authority"] is False

    projection = contract["semantic_projection"]
    assert projection["contract_id"] == "aasm.semantic.projection.v1"
    assert projection["equivalence_contract_id"] == "aasm.semantic.equivalence.v1"
    assert projection["invariant_contract_id"] == "aasm.invariant.v1"
    assert projection["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert projection["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert projection["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert projection["parallel_projection_registry"] == "NONE"
    assert projection["current_projection_pointer"] == "NONE"
    assert projection["invariant_contract"]["classifications"] == [
        "REPRESENTATIONAL", "STATIC_PROTOCOL", "DYNAMIC_KERNEL", "EMPIRICAL"
    ]
    assert all(value == "NONE" for value in projection["public_claim_ceiling"].values())

    uncertainty = contract["uncertainty"]
    assert uncertainty["contract_id"] == "aasm.uncertainty.v1"
    assert uncertainty["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert uncertainty["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert uncertainty["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert uncertainty["parallel_uncertainty_registry"] == "NONE"
    assert uncertainty["current_uncertainty_pointer"] == "NONE"
    assert uncertainty["probability_inference"] == "NONE"
    assert all(value == "NONE" for value in uncertainty["public_claim_ceiling"].values())

    scenario = contract["scenario"]
    assert scenario["contract_id"] == "aasm.scenario.v1"
    assert scenario["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert scenario["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert scenario["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert scenario["scenario_is_problem_revision"] is False
    assert scenario["scenario_is_evidence"] is False
    assert scenario["scenario_activation"] == "NONE_FOUNDATION_ONLY"
    assert scenario["parallel_scenario_registry"] == "NONE"
    assert scenario["hidden_current_scenario"] == "NONE"
    assert all(value == "NONE" for value in scenario["public_claim_ceiling"].values())

    trace_property = contract["trace_property"]
    assert trace_property["contract_id"] == "aasm.trace-property.v1"
    assert trace_property["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert trace_property["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert trace_property["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert trace_property["trace_projection"] == "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"
    assert trace_property["invariant_classification"] == "DYNAMIC_KERNEL"
    assert trace_property["static_constraint_lowering"] == "NONE"
    assert trace_property["parallel_trace_store"] == "NONE"
    assert trace_property["parallel_property_registry"] == "NONE"
    assert all(value == "NONE" for value in trace_property["public_claim_ceiling"].values())

    degraded = contract["degraded_operation"]
    assert degraded["contract_id"] == "aasm.degraded.operation.v1"
    assert degraded["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert degraded["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert degraded["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert degraded["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"
    assert degraded["mode_activation"] == "NONE"
    assert degraded["authority_ceiling"] == "EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED"
    assert degraded["hidden_current_mode"] == "NONE"
    assert degraded["parallel_mode_store"] == "NONE"
    assert degraded["parallel_authority_evaluator"] == "NONE"
    assert degraded["parallel_effect_lifecycle"] == "NONE"
    assert degraded["parallel_dispatcher"] == "NONE"
    assert degraded["mode_selection_grants_effect_authority"] is False
    assert degraded["assessment_is_authorization"] is False
    assert degraded["assessment_activates_mode"] is False
    assert degraded["assessment_proves_safety"] is False
    assert all(value == "NONE" for value in degraded["public_claim_ceiling"].values())

    assert aasm.AASMEngine is public_v56.AASMEngine
    assert not any(name.startswith("rule_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("semantic_projection_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("semantic_equivalence_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("uncertainty_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("scenario_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("trace_property_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("degraded_operation_") for name in aasm.SUPPORTED_ENGINE_METHODS)
