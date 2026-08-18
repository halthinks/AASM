from __future__ import annotations

import aasm
import aasm.public_active_semantic_projection as parent
import aasm.public_active_uncertainty_scenario_trace as active


def subject(semantic_type_id: str, object_id: str, char: str) -> active.SemanticSubjectRef:
    return active.SemanticSubjectRef(
        semantic_type_id,
        object_id,
        char * 64,
        "problem-revision-9",
        "9" * 64,
    )


def scenario() -> active.Scenario:
    return active.Scenario(
        "high-load",
        "problem-revision-9",
        "9" * 64,
        (
            active.ScenarioBinding("mode", "LITERAL", "production"),
            active.ScenarioBinding(
                "load",
                "SEMANTIC_REF",
                value_ref=subject("aasm.quantity.v1", "quantity-load", "a"),
            ),
        ),
        evidence_ids=("evidence-scenario-1",),
    )


def trace_events() -> list[dict[str, object]]:
    return [
        {"event_id": "event-1", "sequence": 1, "event_type": "effect_started", "machine_id": "machine-1"},
        {"event_id": "event-2", "sequence": 2, "event_type": "effect_succeeded", "machine_id": "machine-1"},
    ]


def test_ust_public_adoption_is_additive_over_qualified_03218_parent():
    parent_report = parent.validate_public_api_contract()
    active_report = active.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert active_report["valid"], active_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert active.AASMEngine is parent.AASMEngine
    assert aasm.AASMEngine is active.AASMEngine


def test_ust_public_adoption_preserves_complete_parent_import_and_engine_surfaces():
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(active.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(active.SUPPORTED_INSPECTION_SURFACES)
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert active.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(active, name), name
        assert hasattr(aasm, name), name
    assert "uncertainty-scenario-trace" in active.SUPPORTED_INSPECTION_SURFACES


def test_ust_public_adoption_exports_exact_s44_semantic_ir_without_runtime_methods():
    expected = (
        "UncertaintySpec",
        "ScenarioBinding",
        "Scenario",
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
        assert getattr(aasm, name) is getattr(active, name)
        assert name in aasm.SUPPORTED_PUBLIC_IMPORTS
    assert aasm.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith("uncertainty_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("scenario_") for name in aasm.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("trace_property_") for name in aasm.SUPPORTED_ENGINE_METHODS)


def test_ust_public_adoption_preserves_claim_ceiling_and_parallel_plane_firewalls():
    contract = aasm.public_api_contract()
    uncertainty = contract["uncertainty"]
    scenario_spec = contract["scenario"]
    trace = contract["trace_property"]
    for value in (uncertainty, scenario_spec, trace):
        assert value["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
        assert value["runtime_admission"] == "PRE_ADMISSION_ONLY"
        assert value["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
        assert value["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"
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


def test_ust_public_types_are_deterministic_revision_bound_and_root_accessible():
    item = scenario()
    assert active.Scenario.from_dict(item.to_dict()) == item
    assert aasm.Scenario is active.Scenario
    uncertainty = aasm.UncertaintySpec(
        subject("textpcb.route.v1", "route-1", "b"),
        "SCENARIOS",
        scenario_refs=(item.semantic_ref,),
    )
    assert aasm.UncertaintySpec.from_dict(uncertainty.to_dict()) == uncertainty
    assert uncertainty.scenario_refs == (item.semantic_ref,)


def test_ust_public_trace_evaluator_reuses_existing_trace_without_engine_state():
    prop = aasm.TraceProperty(
        "effect resolves",
        "BOUNDED_EVENTUALLY_STEPS",
        (
            aasm.TraceEventPattern("start", event_types=("effect_started",)),
            aasm.TraceEventPattern("success", event_types=("effect_succeeded",)),
        ),
        max_step_distance=1,
    )
    assessment = aasm.evaluate_trace_property(
        prop,
        trace_events(),
        context=aasm.TraceEvaluationContext("COMPLETE"),
    )
    assert assessment.status == "PASS"
    assert assessment.witness_event_ids == ("event-1", "event-2")
    assert aasm.trace_property_contract()["trace_projection"] == "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"
    assert aasm.trace_property_contract()["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert aasm.AASMEngine is parent.AASMEngine
