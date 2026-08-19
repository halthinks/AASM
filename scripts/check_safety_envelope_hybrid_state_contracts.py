from __future__ import annotations

import json
from pathlib import Path

from aasm.quantity import QUANTITY_CONTRACT_ID, QUANTITY_CONTRACT_VERSION
from aasm.rule import RULE_CONTRACT_ID, RULE_CONTRACT_VERSION, RULE_CLAUSE_KINDS, RULE_STRENGTHS

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        fail(f"missing safety-envelope/hybrid-state contract file: {path}")
    return target.read_text(encoding="utf-8")


def require(source: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in source]
    if missing:
        fail(f"{label} missing required tokens: {missing}")


def forbid(source: str, tokens: tuple[str, ...], label: str) -> None:
    present = [token for token in tokens if token in source]
    if present:
        fail(f"{label} contains forbidden tokens: {present}")


def main() -> None:
    model_paths = (
        "src/aasm/safety_envelope_hybrid_state.py",
        "src/aasm/_safety_envelope_common.py",
        "src/aasm/_safety_envelope_records.py",
        "src/aasm/_hybrid_state_records.py",
        "src/aasm/_safety_envelope_assessment_records.py",
        "src/aasm/_safety_envelope_validation.py",
        "src/aasm/_safety_envelope_evaluation.py",
    )
    model = "\n".join(text(path) for path in model_paths)
    quantity = text("src/aasm/quantity.py")
    rule = text("src/aasm/rule.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    package_root = text("src/aasm/__init__.py")
    tests = text("tests/test_safety_envelope_hybrid_state_foundation.py")
    workflow = text(".github/workflows/engineering-safety-envelope-hybrid-state.yml")

    require(model, (
        'SAFETY_ENVELOPE_CONTRACT_ID = "aasm.safety.envelope.v1"',
        'HYBRID_STATE_CONTRACT_ID = "aasm.hybrid.state.v1"',
        'SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID = "aasm.safety.envelope.assessment.v1"',
        'from .quantity import', 'ExactNumber', 'IntervalValue', 'MeasuredValue', 'Quantity', 'require_canonically_compatible',
        'from .rule import EngineeringRule',
        'from .semantic_evolution import ExternalReference',
        'from .semantic_projection import SemanticSubjectRef',
        'class SafetyEnvelopeConstraint:', 'class SafetyModeEnvelope:', 'class SafetyEnvelope:',
        'class HybridQuantityObservation:', 'class HybridState:',
        'class SafetyConstraintAssessment:', 'class SafetyEnvelopeAssessment:',
        'def bind_safety_constraint(', 'def observe_hybrid_quantity(', 'def unknown_hybrid_quantity(',
        'def validate_safety_envelope(', 'def validate_hybrid_state(', 'def assess_safety_envelope(',
        'rule.strength != "HARD_FLOOR"', 'rule.clause.clause_kind != "SAFETY_INVARIANT"',
        'allowed.representation != "INTERVAL"', 'allowed.tolerance.kind != "NONE"',
        '"UNKNOWN"', '"OVERLAPS_BOUNDARY"', '"UNSUPPORTED"', '"MODE_UNCOVERED"',
        '"ode_solver": "NONE"', '"physics_solver": "NONE"', '"dynamics_integration": "NONE"',
        '"controller_synthesis": "NONE"', '"parallel_safety_state_machine": "NONE"',
        '"parallel_operational_mode_store": "NONE"', '"parallel_rule_system": "NONE"',
        '"parallel_quantity_system": "NONE"', '"parallel_evidence_store": "NONE"',
        '"parallel_authority_evaluator": "NONE"', '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ), "safety-envelope/hybrid-state model")

    forbid(model, (
        "scipy.integrate", "solve_ivp(", "odeint(", "class ODESolver", "class PhysicsSolver",
        "class SafetyStateMachine", "CURRENT_HYBRID_MODE", "CURRENT_SAFETY_MODE", "SAFETY_MODE_REGISTRY",
        "FactAuthority(", "StateClaim(", ".authorize_effect(", ".execute_effect(", "dispatch_effect(",
        "preempt_authority_lease(", "set_obligation_status(", "register_obligation(",
    ), "safety-envelope/hybrid-state model")

    require(quantity, (
        'QUANTITY_CONTRACT_ID = "aasm.quantity.v1"', 'class ExactNumber:', 'class IntervalValue:',
        'class MeasuredValue:', 'class Quantity:', 'def require_canonically_compatible(',
    ), "existing Quantity foundation")
    require(rule, (
        'RULE_CONTRACT_ID = "aasm.rule.v1"', '"HARD_FLOOR"', '"SAFETY_INVARIANT"', 'class EngineeringRule:',
    ), "existing Rule foundation")
    if QUANTITY_CONTRACT_ID != "aasm.quantity.v1" or QUANTITY_CONTRACT_VERSION != "0.1.0":
        fail("live Quantity contract drifted")
    if RULE_CONTRACT_ID != "aasm.rule.v1" or RULE_CONTRACT_VERSION != "0.1.0":
        fail("live Rule contract drifted")
    if "HARD_FLOOR" not in RULE_STRENGTHS or "SAFETY_INVARIANT" not in RULE_CLAUSE_KINDS:
        fail("live Rule safety vocabulary drifted")

    forbid(runtime, (
        "from .safety_envelope_hybrid_state", "SafetyEnvelope", "HybridState", "SafetyEnvelopeAssessment",
    ), "runtime_v56 foundation")
    forbid(package_root, (
        "from .safety_envelope_hybrid_state import", "SafetyEnvelope", "HybridState", "SafetyEnvelopeAssessment",
    ), "active package root")

    schemas = (
        ("schemas/safety-envelope.schema.json", "aasm.safety.envelope.v1"),
        ("schemas/hybrid-state.schema.json", "aasm.hybrid.state.v1"),
        ("schemas/safety-envelope-assessment.schema.json", "aasm.safety.envelope.assessment.v1"),
    )
    for filename, contract_id in schemas:
        schema = json.loads(text(filename))
        if schema.get("additionalProperties") is not False:
            fail(f"{filename} must be closed")
        serialized = json.dumps(schema, sort_keys=True)
        if contract_id not in serialized:
            fail(f"{filename} missing contract ID {contract_id}")
        if '"type": "number"' in serialized:
            fail(f"{filename} admits binary floating-point number identity")

    for token in (
        "test_vocabularies_and_contract_claim_ceiling_are_exact",
        "test_exact_hard_floor_safety_invariant_rule_and_interval_quantity_are_required",
        "test_forged_rule_and_quantity_bindings_fail_closed",
        "test_within_outside_and_boundary_overlap_relations_are_conservative",
        "test_measured_support_and_tolerance_are_expanded_exactly",
        "test_unknown_missing_and_uncovered_mode_fail_closed",
        "test_non_exact_quantization_is_unsupported_not_assumed_safe",
        "test_dimension_and_canonical_unit_mismatch_fail_closed",
        "test_observation_and_mode_provenance_are_mandatory",
        "test_assessment_is_pure_and_cannot_claim_authority_or_solver_execution",
        "test_foundation_is_not_public_root_or_runtime_composition",
        "test_schemas_are_closed_and_accept_canonical_documents",
    ):
        if token not in tests:
            fail(f"safety-envelope/hybrid-state adversarial corpus missing test: {token}")

    require(workflow, (
        "python scripts/check_safety_envelope_hybrid_state_contracts.py",
        "pytest -q tests/test_safety_envelope_hybrid_state_foundation.py",
        "aasm/engineering-safety-envelope-hybrid-state",
        "schemas/safety-envelope.schema.json",
        "schemas/hybrid-state.schema.json",
        "schemas/safety-envelope-assessment.schema.json",
    ), "safety-envelope/hybrid-state workflow")

    print("S4.8 safety-envelope/hybrid-state pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
