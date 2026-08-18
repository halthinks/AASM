from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S4.4 uncertainty/scenario/trace file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/uncertainty_scenario_trace.py")
    uncertainty_schema = json.loads(text("schemas/uncertainty.schema.json"))
    scenario_schema = json.loads(text("schemas/scenario.schema.json"))
    trace_schema = json.loads(text("schemas/trace-property.schema.json"))
    tests = text("tests/test_uncertainty_scenario_trace_foundation.py")
    workflow = text(".github/workflows/engineering-uncertainty-scenario-trace.yml")

    runtime = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active_semantic_projection.py")
    quantity = text("src/aasm/quantity.py")
    tolerance_schema = text("schemas/numeric-tolerance.schema.json")
    semantic_result = text("src/aasm/semantic_result.py")
    semantic_evolution = text("src/aasm/semantic_evolution.py")
    trace = text("src/aasm/trace_conformance.py")
    reproducibility = text("src/aasm/reproducibility.py")

    for token in (
        'UNCERTAINTY_CONTRACT_ID = "aasm.uncertainty.v1"',
        'SCENARIO_CONTRACT_ID = "aasm.scenario.v1"',
        'TRACE_PROPERTY_CONTRACT_ID = "aasm.trace-property.v1"',
        'TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID = "aasm.trace-property.assessment.v1"',
        '"EXACT"',
        '"INTERVAL"',
        '"SCENARIOS"',
        '"DISTRIBUTION_REFERENCE"',
        '"EMPIRICAL_SAMPLES"',
        '"UNKNOWN_BOUNDED"',
        '"UNKNOWN_UNBOUNDED"',
        '"BOUNDED_EVENTUALLY_STEPS"',
        'TRACE_INVARIANT_CLASSIFICATION = "DYNAMIC_KERNEL"',
        "class ScenarioBinding",
        "class Scenario",
        "class UncertaintySpec",
        "class TraceEventPattern",
        "class TraceProperty",
        "class TraceEvaluationContext",
        "class TracePropertyAssessment",
        "def evaluate_trace_property",
        "def uncertainty_contract",
        "def scenario_contract",
        "def trace_property_contract",
        '"NUMERIC_INTERVAL_AND_BOUND_SEMANTICS_REFERENCE_AASM_QUANTITY_V1_NO_DUPLICATE_NUMERIC_ENCODING"',
        '"DISTINCT_FROM_AASM_NUMERIC_TOLERANCE_V1_ACCEPTANCE_POLICY"',
        '"DISTINCT_FROM_SEMANTIC_RESULT_CONFIDENCE_NO_INFERENCE_OR_COERCION"',
        '"EXACT_EXISTING_PROBLEM_REVISION_ID_AND_FINGERPRINT_REQUIRED"',
        '"EXISTING_CHANGED_SCENARIO_IDS_REMAINS_REVISION_INVALIDATION_SEAM_NO_AUTOMATIC_DELTA_CREATION"',
        '"EXISTING_AASM_TRACE_V1_AUTHORITATIVE_DURABLE_EVENT_HISTORY"',
        '"EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"',
        '"PRESERVE_AASM_TRACE_V1_UNSUPPORTED_EXPLICIT"',
        '"EVENT_POSITION_STEPS_ONLY_FOUNDATION_DOES_NOT_INFER_WALL_CLOCK_DURATION"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
        '"parallel_uncertainty_registry": "NONE"',
        '"parallel_scenario_registry": "NONE"',
        '"parallel_trace_store": "NONE"',
        '"parallel_property_registry": "NONE"',
        '"static_constraint_lowering": "NONE"',
    ):
        require(token in model, f"S4.4 semantic foundation missing token: {token}")

    for token in (
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "register_uncertainty(",
        "register_scenario(",
        "activate_scenario(",
        "current_scenario_store",
        "CURRENT_SCENARIO =",
        "UNCERTAINTY_REGISTRY =",
        "TRACE_PROPERTY_REGISTRY =",
        "datetime.now(",
        "time.time(",
        "random.",
        "eval(",
        "exec(",
    ):
        require(token not in model, f"S4.4 semantic foundation violates firewall: {token}")

    require(
        'from .trace_conformance import KNOWN_EVENT_TYPES, TRANSITION_CLASSES, project_trace' in model,
        "trace-property foundation does not reuse existing trace projection",
    )
    require(
        'from .semantic_projection import SemanticSubjectRef' in model,
        "S4.4 foundation does not reuse exact semantic object references",
    )
    require(
        'from .semantic_evolution import ExternalReference' in model,
        "S4.4 foundation does not reuse external-reference semantics",
    )

    for schema, contract_id in (
        (uncertainty_schema, "aasm.uncertainty.v1"),
        (scenario_schema, "aasm.scenario.v1"),
        (trace_schema, "aasm.trace-property.v1"),
    ):
        require(schema.get("additionalProperties") is False, f"{contract_id} schema is not closed")
        require(
            schema["properties"]["contract_id"]["const"] == contract_id,
            f"{contract_id} schema contract identity drift",
        )

    require(
        uncertainty_schema["properties"]["form"]["enum"]
        == [
            "EXACT",
            "INTERVAL",
            "SCENARIOS",
            "DISTRIBUTION_REFERENCE",
            "EMPIRICAL_SAMPLES",
            "UNKNOWN_BOUNDED",
            "UNKNOWN_UNBOUNDED",
        ],
        "uncertainty schema form vocabulary drift",
    )
    require(
        trace_schema["properties"]["invariant_classification"]["const"] == "DYNAMIC_KERNEL",
        "trace-property invariant classification drift",
    )

    require("class IntervalValue" in quantity and "class MeasuredValue" in quantity, "Quantity uncertainty substrate missing")
    require(
        '"uncertainty": "MEASURED_OR_ESTIMATED_VALUES_REQUIRE_INTERVAL_AND_EXTERNAL_REFERENCE"' in quantity,
        "Quantity measured uncertainty contract drift",
    )
    require('"aasm.numeric.tolerance.v1"' in tolerance_schema, "numeric tolerance substrate drift")
    require("confidence: float | None = None" in semantic_result, "existing semantic-result confidence surface drift")
    require("changed_scenario_ids" in semantic_evolution, "ProblemDelta scenario invalidation seam missing")
    require('TRACE_CONTRACT_ID = "aasm.trace.v1"' in trace, "existing trace contract drift")
    require("def project_trace" in trace, "existing trace projection function missing")
    require('"unknown_transition_policy": "UNSUPPORTED_EXPLICIT"' in trace, "trace unsupported policy drift")
    require('REPRODUCIBILITY_RUN_CONTRACT_ID = "aasm.solver.reproducibility-run.v1"' in reproducibility, "reproducibility substrate drift")

    for source, label in (
        (runtime, "runtime_v56_foundation"),
        (public, "active 0.32.18 public root"),
        (quantity, "Quantity foundation"),
        (semantic_result, "SemanticResult"),
        (semantic_evolution, "ProblemRevision/ProblemDelta"),
        (trace, "trace conformance"),
        (reproducibility, "solver reproducibility"),
    ):
        require(
            "from .uncertainty_scenario_trace" not in source,
            f"S4.4 foundation leaked into {label} before admission",
        )
        require(
            "aasm.uncertainty.v1" not in source,
            f"uncertainty contract leaked into {label} before admission",
        )
        require(
            "aasm.scenario.v1" not in source,
            f"scenario contract leaked into {label} before admission",
        )
        require(
            "aasm.trace-property.v1" not in source,
            f"trace-property contract leaked into {label} before admission",
        )

    for token in (
        "test_contract_vocabularies_are_exact_and_pre_admission",
        "test_uncertainty_contract_does_not_reinterpret_quantity_tolerance_confidence_or_probability",
        "test_uncertainty_forms_are_structurally_distinct_and_deterministic",
        "test_uncertainty_shape_errors_fail_closed",
        "test_scenario_is_revision_bound_hypothesis_not_problem_revision_or_authority",
        "test_scenario_literal_and_revision_attacks_fail_closed",
        "test_binary_float_metadata_is_rejected_across_all_three_contracts",
        "test_trace_property_uses_existing_trace_v1_and_requires_dynamic_kernel_classification",
        "test_complete_trace_occurs_sequence_and_bounded_eventual_properties_pass",
        "test_trace_property_failures_preserve_witness_and_violation_information",
        "test_trace_prefix_unknown_revision_mismatch_and_unsupported_events_fail_closed",
        "test_invalid_trace_projection_and_unknown_pattern_type_do_not_become_property_truth",
        "test_tampered_identifiers_and_fingerprints_fail_closed_on_round_trip",
        "test_primary_json_schemas_are_closed_and_accept_canonical_records",
    ):
        require(token in tests, f"S4.4 adversarial corpus missing test: {token}")

    for token in (
        "check_uncertainty_scenario_trace_contracts.py",
        "tests/test_uncertainty_scenario_trace_foundation.py",
        "schemas/uncertainty.schema.json",
        "schemas/scenario.schema.json",
        "schemas/trace-property.schema.json",
        "context='aasm/engineering-uncertainty-scenario-trace'",
    ):
        require(token in workflow, f"S4.4 workflow missing token: {token}")

    print("S4.4 uncertainty/scenario/trace-property pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
