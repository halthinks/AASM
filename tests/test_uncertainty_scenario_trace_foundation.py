from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

from aasm.semantic_evolution import ExternalReference
from aasm.semantic_projection import SemanticSubjectRef
from aasm.uncertainty_scenario_trace import (
    SCENARIO_BINDING_KINDS,
    TRACE_COMPLETENESS,
    TRACE_INVARIANT_CLASSIFICATION,
    TRACE_PROPERTY_KINDS,
    TRACE_PROPERTY_STATUSES,
    UNCERTAINTY_FORMS,
    Scenario,
    ScenarioBinding,
    TraceEvaluationContext,
    TraceEventPattern,
    TraceProperty,
    UncertaintySpec,
    evaluate_trace_property,
    scenario_contract,
    trace_property_contract,
    uncertainty_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def ref(
    semantic_type_id: str,
    object_id: str,
    char: str,
    *,
    revision_id: str = "problem-revision-7",
    revision_fingerprint: str = "7" * 64,
) -> SemanticSubjectRef:
    return SemanticSubjectRef(
        semantic_type_id,
        object_id,
        char * 64,
        revision_id,
        revision_fingerprint,
    )


def scenario(name: str = "hot-ambient", **overrides) -> Scenario:
    payload = {
        "scenario_name": name,
        "base_problem_revision_id": "problem-revision-7",
        "base_problem_revision_fingerprint": "7" * 64,
        "bindings": (
            ScenarioBinding("mode", "LITERAL", "production"),
            ScenarioBinding(
                "ambient",
                "SEMANTIC_REF",
                value_ref=ref("aasm.quantity.v1", "quantity-ambient", "a"),
            ),
        ),
        "evidence_ids": ("evidence-scenario-source",),
        "tags": ("thermal",),
    }
    payload.update(overrides)
    return Scenario(**payload)


def events() -> list[dict[str, object]]:
    return [
        {
            "event_id": "e1",
            "sequence": 1,
            "event_type": "machine_created",
            "machine_id": "m1",
        },
        {
            "event_id": "e2",
            "sequence": 2,
            "event_type": "effect_started",
            "machine_id": "m1",
        },
        {
            "event_id": "e3",
            "sequence": 3,
            "event_type": "effect_succeeded",
            "machine_id": "m1",
        },
    ]


def pattern(pattern_id: str, event_type: str) -> TraceEventPattern:
    return TraceEventPattern(pattern_id, event_types=(event_type,))


def complete_context() -> TraceEvaluationContext:
    return TraceEvaluationContext(
        "COMPLETE",
        "problem-revision-7",
        "7" * 64,
    )


def test_contract_vocabularies_are_exact_and_pre_admission():
    assert UNCERTAINTY_FORMS == (
        "EXACT",
        "INTERVAL",
        "SCENARIOS",
        "DISTRIBUTION_REFERENCE",
        "EMPIRICAL_SAMPLES",
        "UNKNOWN_BOUNDED",
        "UNKNOWN_UNBOUNDED",
    )
    assert SCENARIO_BINDING_KINDS == ("LITERAL", "SEMANTIC_REF")
    assert TRACE_PROPERTY_KINDS == (
        "OCCURS",
        "NEVER_OCCURS",
        "PRECEDES",
        "SEQUENCE",
        "BOUNDED_EVENTUALLY_STEPS",
    )
    assert TRACE_COMPLETENESS == ("COMPLETE", "PREFIX", "UNKNOWN")
    assert TRACE_PROPERTY_STATUSES == ("PASS", "FAIL", "INCONCLUSIVE", "UNSUPPORTED")
    assert TRACE_INVARIANT_CLASSIFICATION == "DYNAMIC_KERNEL"

    uncertainty = uncertainty_contract()
    scenario_spec = scenario_contract()
    trace = trace_property_contract()
    assert uncertainty["contract_id"] == "aasm.uncertainty.v1"
    assert scenario_spec["contract_id"] == "aasm.scenario.v1"
    assert trace["contract_id"] == "aasm.trace-property.v1"
    assert uncertainty["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert scenario_spec["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert trace["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert uncertainty["public_admission"] == "PRE_ADMISSION_ONLY"
    assert scenario_spec["public_admission"] == "PRE_ADMISSION_ONLY"
    assert trace["public_admission"] == "PRE_ADMISSION_ONLY"


def test_uncertainty_contract_does_not_reinterpret_quantity_tolerance_confidence_or_probability():
    contract = uncertainty_contract()
    assert contract["quantity_relation"] == "NUMERIC_INTERVAL_AND_BOUND_SEMANTICS_REFERENCE_AASM_QUANTITY_V1_NO_DUPLICATE_NUMERIC_ENCODING"
    assert contract["numeric_tolerance_relation"] == "DISTINCT_FROM_AASM_NUMERIC_TOLERANCE_V1_ACCEPTANCE_POLICY"
    assert contract["confidence_relation"] == "DISTINCT_FROM_SEMANTIC_RESULT_CONFIDENCE_NO_INFERENCE_OR_COERCION"
    assert contract["probability_inference"] == "NONE"
    assert contract["truth_authority"] == "NONE"
    assert contract["fact_authority"] == "NONE"
    assert contract["effect_authority"] == "NONE"
    assert contract["objective_preference"] == "NONE"
    assert contract["reuse_admission"] == "NONE"
    assert contract["parallel_uncertainty_registry"] == "NONE"
    assert contract["current_uncertainty_pointer"] == "NONE"


def test_uncertainty_forms_are_structurally_distinct_and_deterministic():
    subject = ref("textpcb.route.v1", "route-1", "b")
    exact = UncertaintySpec(subject, "EXACT")
    assert UncertaintySpec.from_dict(exact.to_dict()) == exact

    interval = UncertaintySpec(
        subject,
        "INTERVAL",
        interval_quantity=ref("aasm.quantity.v1", "quantity-interval", "c"),
    )
    assert interval.form == "INTERVAL"

    first_scenario = scenario("hot")
    second_scenario = scenario("cold")
    scenarios = UncertaintySpec(
        subject,
        "SCENARIOS",
        scenario_refs=(second_scenario.semantic_ref, first_scenario.semantic_ref),
    )
    assert [row.object_id for row in scenarios.scenario_refs] == sorted(
        [first_scenario.scenario_id, second_scenario.scenario_id]
    )

    distribution = ExternalReference(
        "model",
        "thermal-distribution",
        "uncertainty_distribution",
        revision="v3",
        source_fingerprint="d" * 64,
    )
    distribution_spec = UncertaintySpec(
        subject,
        "DISTRIBUTION_REFERENCE",
        distribution_reference=distribution,
    )
    assert distribution_spec.distribution_reference == distribution

    samples = UncertaintySpec(
        subject,
        "EMPIRICAL_SAMPLES",
        sample_refs=(ref("aasm.quantity.v1", "sample-1", "e"),),
        evidence_ids=("evidence-sample-1",),
    )
    assert samples.evidence_ids == ("evidence-sample-1",)

    bounded = UncertaintySpec(
        subject,
        "UNKNOWN_BOUNDED",
        bound_quantity=ref("aasm.quantity.v1", "unknown-bound", "f"),
    )
    assert bounded.bound_quantity is not None
    assert UncertaintySpec(subject, "UNKNOWN_UNBOUNDED").form == "UNKNOWN_UNBOUNDED"


def test_uncertainty_shape_errors_fail_closed():
    subject = ref("textpcb.route.v1", "route-1", "b")
    quantity = ref("aasm.quantity.v1", "quantity-1", "c")
    with pytest.raises(ValueError, match="requires exactly"):
        UncertaintySpec(subject, "EXACT", interval_quantity=quantity)
    with pytest.raises(ValueError, match="aasm.quantity.v1"):
        UncertaintySpec(
            subject,
            "INTERVAL",
            interval_quantity=ref("textpcb.interval.v1", "interval-1", "d"),
        )
    with pytest.raises(ValueError, match="source_fingerprint"):
        UncertaintySpec(
            subject,
            "DISTRIBUTION_REFERENCE",
            distribution_reference=ExternalReference(
                "model",
                "distribution",
                "uncertainty_distribution",
                revision="v1",
            ),
        )
    with pytest.raises(ValueError, match="evidence_ids"):
        UncertaintySpec(
            subject,
            "EMPIRICAL_SAMPLES",
            sample_refs=(ref("aasm.quantity.v1", "sample-1", "e"),),
        )


def test_scenario_is_revision_bound_hypothesis_not_problem_revision_or_authority():
    item = scenario()
    restored = Scenario.from_dict(item.to_dict())
    assert restored == item
    assert item.semantic_ref.semantic_type_id == "aasm.scenario.v1"
    assert item.semantic_ref.revision_id == "problem-revision-7"
    contract = scenario_contract()
    assert contract["scenario_is_problem_revision"] is False
    assert contract["scenario_is_evidence"] is False
    assert contract["scenario_activation"] == "NONE_FOUNDATION_ONLY"
    assert contract["scenario_selection_grants_authority"] is False
    assert contract["scenario_existence_grants_fact_authority"] is False
    assert contract["scenario_existence_grants_effect_authority"] is False
    assert contract["hidden_current_scenario"] == "NONE"
    assert contract["parallel_scenario_registry"] == "NONE"


def test_scenario_literal_and_revision_attacks_fail_closed():
    with pytest.raises(TypeError, match="numeric engineering values"):
        ScenarioBinding("temperature", "LITERAL", 22.5)
    with pytest.raises(ValueError, match="unique"):
        Scenario(
            "duplicate",
            "problem-revision-7",
            "7" * 64,
            (
                ScenarioBinding("mode", "LITERAL", "a"),
                ScenarioBinding("mode", "LITERAL", "b"),
            ),
        )
    with pytest.raises(ValueError, match="64-hex"):
        Scenario(
            "bad-revision",
            "problem-revision-7",
            "not-a-fingerprint",
            (ScenarioBinding("mode", "LITERAL", "a"),),
        )


def test_binary_float_metadata_is_rejected_across_all_three_contracts():
    with pytest.raises(TypeError, match="binary floating-point"):
        scenario(metadata={"weight": 0.5})
    with pytest.raises(TypeError, match="binary floating-point"):
        UncertaintySpec(
            ref("textpcb.route.v1", "route-1", "b"),
            "EXACT",
            metadata={"confidence": 0.5},
        )
    with pytest.raises(TypeError, match="binary floating-point"):
        TraceEventPattern("bad", event_types=("machine_created",), metadata={"score": 0.5})


def test_trace_property_uses_existing_trace_v1_and_requires_dynamic_kernel_classification():
    contract = trace_property_contract()
    assert contract["trace_source"] == "EXISTING_AASM_TRACE_V1_AUTHORITATIVE_DURABLE_EVENT_HISTORY"
    assert contract["trace_projection"] == "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"
    assert contract["unsupported_transition_policy"] == "PRESERVE_AASM_TRACE_V1_UNSUPPORTED_EXPLICIT"
    assert contract["invariant_classification"] == "DYNAMIC_KERNEL"
    assert contract["static_constraint_lowering"] == "NONE"
    assert contract["host_wall_clock"] == "NONE"
    assert contract["assessment_grants_truth"] is False
    assert contract["assessment_grants_fact_authority"] is False
    assert contract["assessment_grants_effect_authority"] is False
    assert contract["assessment_is_solver_proof"] is False
    with pytest.raises(ValueError, match="DYNAMIC_KERNEL"):
        TraceProperty(
            "bad-static",
            "OCCURS",
            (pattern("created", "machine_created"),),
            invariant_classification="STATIC_PROTOCOL",
        )


def test_complete_trace_occurs_sequence_and_bounded_eventual_properties_pass():
    occurs = TraceProperty(
        "effect succeeds",
        "OCCURS",
        (pattern("success", "effect_succeeded"),),
        problem_revision_id="problem-revision-7",
        problem_revision_fingerprint="7" * 64,
    )
    assert evaluate_trace_property(occurs, events(), context=complete_context()).status == "PASS"

    sequence = TraceProperty(
        "lifecycle",
        "SEQUENCE",
        (
            pattern("created", "machine_created"),
            pattern("started", "effect_started"),
            pattern("success", "effect_succeeded"),
        ),
    )
    sequence_assessment = evaluate_trace_property(
        sequence, events(), context=TraceEvaluationContext("COMPLETE")
    )
    assert sequence_assessment.status == "PASS"
    assert sequence_assessment.witness_event_ids == ("e1", "e2", "e3")

    bounded = TraceProperty(
        "effect resolves promptly",
        "BOUNDED_EVENTUALLY_STEPS",
        (pattern("started", "effect_started"), pattern("success", "effect_succeeded")),
        max_step_distance=1,
    )
    assert evaluate_trace_property(
        bounded, events(), context=TraceEvaluationContext("COMPLETE")
    ).status == "PASS"


def test_trace_property_failures_preserve_witness_and_violation_information():
    bad_order = [events()[0], events()[2], events()[1]]
    for index, row in enumerate(bad_order, start=1):
        row["sequence"] = index
    precedes = TraceProperty(
        "start before success",
        "PRECEDES",
        (pattern("started", "effect_started"), pattern("success", "effect_succeeded")),
    )
    assessment = evaluate_trace_property(
        precedes, bad_order, context=TraceEvaluationContext("COMPLETE")
    )
    assert assessment.status == "FAIL"
    assert assessment.violating_event_ids == ("e3",)
    assert "PRECEDENCE_VIOLATION" in assessment.diagnostics

    too_slow = [
        events()[0],
        events()[1],
        {
            "event_id": "e-x",
            "sequence": 3,
            "event_type": "proposal",
            "machine_id": "m1",
        },
        {**events()[2], "sequence": 4},
    ]
    bounded = TraceProperty(
        "bounded",
        "BOUNDED_EVENTUALLY_STEPS",
        (pattern("started", "effect_started"), pattern("success", "effect_succeeded")),
        max_step_distance=1,
    )
    assessment = evaluate_trace_property(
        bounded, too_slow, context=TraceEvaluationContext("COMPLETE")
    )
    assert assessment.status == "FAIL"
    assert assessment.violating_event_ids == ("e2",)


def test_trace_prefix_unknown_revision_mismatch_and_unsupported_events_fail_closed():
    prop = TraceProperty(
        "effect succeeds",
        "OCCURS",
        (pattern("success", "effect_succeeded"),),
        problem_revision_id="problem-revision-7",
        problem_revision_fingerprint="7" * 64,
    )
    prefix = evaluate_trace_property(
        prop,
        events(),
        context=TraceEvaluationContext(
            "PREFIX", "problem-revision-7", "7" * 64
        ),
    )
    assert prefix.status == "INCONCLUSIVE"
    assert prefix.diagnostics == ("TRACE_NOT_DECLARED_COMPLETE",)

    mismatch = evaluate_trace_property(
        prop,
        events(),
        context=TraceEvaluationContext(
            "COMPLETE", "problem-revision-8", "8" * 64
        ),
    )
    assert mismatch.status == "INCONCLUSIVE"
    assert mismatch.diagnostics == ("PROBLEM_REVISION_MISMATCH",)

    unsupported_events = events() + [
        {
            "event_id": "e4",
            "sequence": 4,
            "event_type": "future_unknown_event",
            "machine_id": "m1",
        }
    ]
    unsupported = evaluate_trace_property(
        TraceProperty("created", "OCCURS", (pattern("created", "machine_created"),)),
        unsupported_events,
        context=TraceEvaluationContext("COMPLETE"),
    )
    assert unsupported.status == "UNSUPPORTED"
    assert unsupported.diagnostics == ("UNSUPPORTED_EVENT_TYPE:future_unknown_event",)


def test_invalid_trace_projection_and_unknown_pattern_type_do_not_become_property_truth():
    non_monotonic = events()
    non_monotonic[2]["sequence"] = 2
    prop = TraceProperty("created", "OCCURS", (pattern("created", "machine_created"),))
    assessment = evaluate_trace_property(
        prop, non_monotonic, context=TraceEvaluationContext("COMPLETE")
    )
    assert assessment.status == "INCONCLUSIVE"
    assert assessment.diagnostics == ("TRACE_PROJECTION_INVALID",)
    with pytest.raises(ValueError, match="unsupported event types"):
        TraceEventPattern("future", event_types=("future_unknown_event",))


def test_tampered_identifiers_and_fingerprints_fail_closed_on_round_trip():
    item = scenario()
    changed = deepcopy(item.to_dict())
    changed["scenario_id"] = "scenario-" + "0" * 24
    with pytest.raises(ValueError, match="scenario_id"):
        Scenario.from_dict(changed)

    uncertainty = UncertaintySpec(
        ref("textpcb.route.v1", "route-1", "b"), "EXACT"
    )
    changed = deepcopy(uncertainty.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="uncertainty fingerprint"):
        UncertaintySpec.from_dict(changed)

    prop = TraceProperty("created", "OCCURS", (pattern("created", "machine_created"),))
    changed = deepcopy(prop.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="trace property fingerprint"):
        TraceProperty.from_dict(changed)


def test_primary_json_schemas_are_closed_and_accept_canonical_records():
    records = (
        (
            "uncertainty.schema.json",
            UncertaintySpec(ref("textpcb.route.v1", "route-1", "b"), "EXACT").to_dict(),
        ),
        ("scenario.schema.json", scenario().to_dict()),
        (
            "trace-property.schema.json",
            TraceProperty(
                "created",
                "OCCURS",
                (pattern("created", "machine_created"),),
            ).to_dict(),
        ),
    )
    for name, record in records:
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(record, schema)
        changed = deepcopy(record)
        changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
