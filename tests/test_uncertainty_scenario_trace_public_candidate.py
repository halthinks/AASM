from __future__ import annotations

import aasm
import aasm.public_active_semantic_projection as parent
import aasm.public_active_uncertainty_scenario_trace as candidate


def subject(
    semantic_type_id: str,
    object_id: str,
    char: str,
) -> candidate.SemanticSubjectRef:
    return candidate.SemanticSubjectRef(
        semantic_type_id,
        object_id,
        char * 64,
        "problem-revision-9",
        "9" * 64,
    )


def scenario() -> candidate.Scenario:
    return candidate.Scenario(
        "high-load",
        "problem-revision-9",
        "9" * 64,
        (
            candidate.ScenarioBinding("mode", "LITERAL", "production"),
            candidate.ScenarioBinding(
                "load",
                "SEMANTIC_REF",
                value_ref=subject("aasm.quantity.v1", "quantity-load", "a"),
            ),
        ),
        evidence_ids=("evidence-scenario-1",),
    )


def trace_events() -> list[dict[str, object]]:
    return [
        {
            "event_id": "event-1",
            "sequence": 1,
            "event_type": "effect_started",
            "machine_id": "machine-1",
        },
        {
            "event_id": "event-2",
            "sequence": 2,
            "event_type": "effect_succeeded",
            "machine_id": "machine-1",
        },
    ]


def test_uncertainty_scenario_trace_public_candidate_advances_only_candidate_overlay():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert candidate_report["valid"], candidate_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert candidate.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert "uncertainty" not in aasm.PUBLIC_API_CONTRACT
    assert "scenario" not in aasm.PUBLIC_API_CONTRACT
    assert "trace_property" not in aasm.PUBLIC_API_CONTRACT


def test_active_package_root_remains_03218_until_ust_candidate_is_qualified():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert aasm.AASMEngine is parent.AASMEngine
    assert not hasattr(aasm, "UncertaintySpec")
    assert not hasattr(aasm, "ScenarioBinding")
    assert not hasattr(aasm, "TraceProperty")


def test_ust_candidate_preserves_complete_parent_public_surface_and_engine_identity():
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert candidate.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(candidate.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(candidate.SUPPORTED_INSPECTION_SURFACES)
    assert "uncertainty-scenario-trace" in candidate.SUPPORTED_INSPECTION_SURFACES
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(candidate, name), name


def test_ust_candidate_exports_complete_s44_ir_without_engine_methods():
    expected = (
        "UNCERTAINTY_CONTRACT_ID",
        "UNCERTAINTY_CONTRACT_VERSION",
        "SCENARIO_CONTRACT_ID",
        "SCENARIO_CONTRACT_VERSION",
        "TRACE_PROPERTY_CONTRACT_ID",
        "TRACE_PROPERTY_CONTRACT_VERSION",
        "TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID",
        "UNCERTAINTY_FORMS",
        "SCENARIO_BINDING_KINDS",
        "TRACE_PROPERTY_KINDS",
        "TRACE_COMPLETENESS",
        "TRACE_PROPERTY_STATUSES",
        "TRACE_INVARIANT_CLASSIFICATION",
        "ScenarioBinding",
        "Scenario",
        "UncertaintySpec",
        "TraceEventPattern",
        "TraceProperty",
        "TraceEvaluationContext",
        "TracePropertyAssessment",
        "evaluate_trace_property",
        "uncertainty_contract",
        "scenario_contract",
        "trace_property_contract",
    )
    for name in expected:
        assert hasattr(candidate, name), name
        assert name in candidate.SUPPORTED_PUBLIC_IMPORTS
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith("uncertainty_") for name in candidate.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("scenario_") for name in candidate.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("trace_property_") for name in candidate.SUPPORTED_ENGINE_METHODS)


def test_ust_candidate_contract_preserves_claim_ceiling_and_no_parallel_planes():
    contract = candidate.public_api_contract()
    uncertainty = contract["uncertainty"]
    scenario_spec = contract["scenario"]
    trace = contract["trace_property"]

    assert uncertainty["contract_id"] == "aasm.uncertainty.v1"
    assert scenario_spec["contract_id"] == "aasm.scenario.v1"
    assert trace["contract_id"] == "aasm.trace-property.v1"
    for value in (uncertainty, scenario_spec, trace):
        assert value["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
        assert value["runtime_admission"] == "PRE_ADMISSION_ONLY"
        assert value["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
        assert value["active_root_status"] == "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"
        assert all(entry == "NONE" for entry in value["public_claim_ceiling"].values())

    assert uncertainty["parallel_uncertainty_registry"] == "NONE"
    assert uncertainty["current_uncertainty_pointer"] == "NONE"
    assert scenario_spec["parallel_scenario_registry"] == "NONE"
    assert scenario_spec["hidden_current_scenario"] == "NONE"
    assert scenario_spec["scenario_activation"] == "NONE_FOUNDATION_ONLY"
    assert scenario_spec["scenario_is_problem_revision"] is False
    assert scenario_spec["scenario_is_evidence"] is False
    assert trace["parallel_trace_store"] == "NONE"
    assert trace["parallel_property_registry"] == "NONE"
    assert trace["static_constraint_lowering"] == "NONE"
    assert trace["invariant_classification"] == "DYNAMIC_KERNEL"
    assert trace["assessment_grants_truth"] is False
    assert trace["assessment_grants_fact_authority"] is False
    assert trace["assessment_grants_effect_authority"] is False


def test_ust_candidate_public_types_are_deterministic_and_revision_bound():
    item = scenario()
    restored = candidate.Scenario.from_dict(item.to_dict())
    assert restored == item
    assert item.semantic_ref.semantic_type_id == "aasm.scenario.v1"
    assert item.semantic_ref.revision_id == "problem-revision-9"

    uncertainty = candidate.UncertaintySpec(
        subject("textpcb.route.v1", "route-1", "b"),
        "SCENARIOS",
        scenario_refs=(item.semantic_ref,),
    )
    assert candidate.UncertaintySpec.from_dict(uncertainty.to_dict()) == uncertainty
    assert uncertainty.scenario_refs == (item.semantic_ref,)


def test_ust_candidate_trace_evaluator_is_semantic_only_and_reuses_existing_trace_projection():
    prop = candidate.TraceProperty(
        "effect resolves",
        "BOUNDED_EVENTUALLY_STEPS",
        (
            candidate.TraceEventPattern("start", event_types=("effect_started",)),
            candidate.TraceEventPattern("success", event_types=("effect_succeeded",)),
        ),
        max_step_distance=1,
    )
    assessment = candidate.evaluate_trace_property(
        prop,
        trace_events(),
        context=candidate.TraceEvaluationContext("COMPLETE"),
    )
    assert assessment.status == "PASS"
    assert assessment.witness_event_ids == ("event-1", "event-2")
    assert candidate.trace_property_contract()["trace_projection"] == "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"
    assert candidate.trace_property_contract()["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert candidate.AASMEngine is parent.AASMEngine
