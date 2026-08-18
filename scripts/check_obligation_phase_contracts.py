from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        fail(f"missing obligation-phase contract file: {path}")
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
    model = text("src/aasm/obligation_phase.py")
    calculus_model = text("src/aasm/_calculus_model.py")
    calculus_runtime = text("src/aasm/runtime_v21.py")
    runtime_v56 = text("src/aasm/runtime_v56_foundation.py")
    package_root = text("src/aasm/__init__.py")
    tests = text("tests/test_obligation_phase_foundation.py")
    workflow = text(".github/workflows/engineering-obligation-phase.yml")

    require(model, (
        'OBLIGATION_PHASE_CONTRACT_ID = "aasm.obligation.phase.v1"',
        'OBLIGATION_PHASE_CONTRACT_VERSION = "0.1.0"',
        'OBLIGATION_PHASE_BINDING_CONTRACT_ID = "aasm.obligation.phase-binding.v1"',
        'OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID = "aasm.obligation.phase-assessment.v1"',
        '"PRE_AUTHORIZE"',
        '"PRE_DISPATCH"',
        '"POST_DISPATCH"',
        '"POST_OBSERVE"',
        '"POST_VERIFY"',
        '"RECOVERY"',
        'from .calculus import (',
        'OBLIGATION_STATUSES',
        'OBLIGATION_TRANSITIONS',
        'ObligationRecord',
        'normalize_calculus_state',
        'obligation_fingerprint',
        'from .scopes import ROOT_SCOPE_ID, scope_id_from, with_scope',
        'class ObligationPhaseBinding:',
        'class ObligationPhasePlan:',
        'class ObligationPhaseAssessment:',
        'def bind_obligation_phase(',
        'def validate_obligation_phase_binding(',
        'def validate_obligation_phase_plan(',
        'def assess_obligation_phase_readiness(',
        '"obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY"',
        '"obligation_edges": "EXISTING_AASM_CALCULUS_V1_REQUIRES_EDGES_ONLY"',
        '"obligation_status_machine": "EXISTING_AASM_CALCULUS_V1_OBLIGATION_TRANSITIONS_UNCHANGED"',
        '"recovery_phase_order": "ORTHOGONAL_NO_IMPLICIT_PRECEDENCE"',
        '"plan_coverage": "EXACTLY_ONE_BINDING_PER_EXISTING_OBLIGATION_FAIL_CLOSED"',
        '"obligation_mutation": "NONE"',
        '"phase_activation": "NONE"',
        '"effect_authorization": "NONE"',
        '"effect_dispatch": "NONE"',
        '"recovery_execution": "NONE"',
        '"current_phase_pointer": "NONE"',
        '"parallel_obligation_store": "NONE"',
        '"parallel_obligation_lifecycle": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"parallel_dispatcher": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ), "obligation-phase model")

    forbid(model, (
        "class ObligationRecord:",
        "\nOBLIGATION_STATUSES =",
        "\nOBLIGATION_TRANSITIONS =",
        "\nOBLIGATION_STORE =",
        "\nOBLIGATION_REGISTRY =",
        "\nOBLIGATION_PHASE_REGISTRY =",
        "\nCURRENT_OBLIGATION_PHASE =",
        "\nCURRENT_PHASE =",
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "preempt_authority_lease(",
        "set_obligation_status(",
        "register_obligation(",
        "enable_obligation(",
    ), "obligation-phase model")

    require(calculus_model, (
        'CALCULUS_CONTRACT_ID = "aasm.calculus.v1"',
        'class ObligationRecord:',
        'OBLIGATION_TRANSITIONS = {',
        '"AVAILABLE": {"ENABLED", "BLOCKED", "LOCKED", "SUPERSEDED", "IMPOSSIBLE"}',
        '"VERIFIED": {"COMMITTED", "NEEDS_REVALIDATION", "REJECTED"}',
    ), "existing calculus model")
    require(calculus_runtime, (
        'def register_obligation(',
        'state["obligation_edges"].append({"src": dependency, "dst": record.obligation_id, "relation": "REQUIRES"})',
        'def enable_obligation(',
        'def set_obligation_status(',
        'status not in OBLIGATION_TRANSITIONS.get(current_status, set())',
    ), "existing obligation runtime")

    forbid(runtime_v56, (
        "from .obligation_phase",
        "ObligationPhaseBinding",
        "ObligationPhasePlan",
        "ObligationPhaseAssessment",
    ), "runtime_v56 foundation")
    forbid(package_root, (
        "from .obligation_phase import",
        "ObligationPhaseBinding",
        "ObligationPhasePlan",
        "ObligationPhaseAssessment",
    ), "active package root")

    for filename, contract_id in (
        ("schemas/obligation-phase-binding.schema.json", "aasm.obligation.phase-binding.v1"),
        ("schemas/obligation-phase-plan.schema.json", "aasm.obligation.phase.v1"),
        ("schemas/obligation-phase-assessment.schema.json", "aasm.obligation.phase-assessment.v1"),
    ):
        schema = json.loads(text(filename))
        if schema.get("additionalProperties") is not False:
            fail(f"{filename} must be closed")
        serialized = json.dumps(schema, sort_keys=True)
        if contract_id not in serialized:
            fail(f"{filename} missing contract ID {contract_id}")
        if "RECOVERY" not in serialized and "assessment" not in filename:
            fail(f"{filename} missing RECOVERY phase vocabulary")

    for token in (
        "test_phase_vocabulary_order_and_recovery_orthogonality_are_exact",
        "test_binding_uses_exact_existing_obligation_fingerprint_scope_and_revision",
        "test_obligation_status_changes_do_not_stale_binding_but_semantic_requirement_changes_do",
        "test_plan_requires_exactly_one_binding_for_every_existing_obligation",
        "test_forward_normal_dependency_is_valid_and_backward_normal_dependency_fails_closed",
        "test_recovery_dependencies_are_explicit_edges_without_implicit_phase_order",
        "test_phase_readiness_uses_existing_status_machine_without_mutating_it",
        "test_terminal_obligation_disposition_is_not_treated_as_phase_success",
        "test_existing_obligation_status_machine_is_not_redefined_or_weakened",
        "test_foundation_is_not_public_root_or_runtime_composition",
    ):
        if token not in tests:
            fail(f"obligation-phase adversarial corpus missing test: {token}")

    require(workflow, (
        "python scripts/check_obligation_phase_contracts.py",
        "pytest -q tests/test_obligation_phase_foundation.py",
        "aasm/engineering-obligation-phase",
        "schemas/obligation-phase-binding.schema.json",
        "schemas/obligation-phase-plan.schema.json",
        "schemas/obligation-phase-assessment.schema.json",
    ), "obligation-phase workflow")

    print("S4.7 aasm.obligation.phase.v1 pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
