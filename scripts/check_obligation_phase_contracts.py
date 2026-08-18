from __future__ import annotations

import json
from pathlib import Path

from aasm.calculus import OBLIGATION_STATUSES, OBLIGATION_TRANSITIONS, default_calculus_state


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_OBLIGATION_TRANSITIONS = {
    "AVAILABLE": {"ENABLED", "BLOCKED", "LOCKED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "ENABLED": {"IN_PROGRESS", "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "IN_PROGRESS": {"VERIFYING", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "VERIFYING": {"VERIFIED", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "VERIFIED": {"COMMITTED", "NEEDS_REVALIDATION", "SUPERSEDED"},
    "COMMITTED": {"NEEDS_REVALIDATION", "SUPERSEDED"},
    "BLOCKED": {"AVAILABLE", "ENABLED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "LOCKED": {"AVAILABLE", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "NEEDS_REVALIDATION": {"AVAILABLE", "ENABLED", "VERIFYING", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "REJECTED": set(),
    "SUPERSEDED": set(),
    "IMPOSSIBLE": set(),
}
EXPECTED_OBLIGATION_STATUSES = set(EXPECTED_OBLIGATION_TRANSITIONS)


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
    calculus_public = text("src/aasm/calculus.py")
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
        'CALCULUS_SUBSTRATE_ID = "aasm.calculus.v1"',
        'CALCULUS_STATE_SCHEMA_VERSION = 1',
        'OBLIGATION_BINDING_PROJECTION_ID = "aasm.obligation.phase.binding-projection.v1"',
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
        'content_hash',
        'normalize_calculus_state',
        'from .scopes import ROOT_SCOPE_ID, scope_id_from, with_scope',
        'def obligation_binding_projection(',
        'def obligation_semantic_fingerprint(',
        'return content_hash(obligation_binding_projection(value))',
        'class ObligationPhaseBinding:',
        'obligation_semantic_fingerprint: str',
        'class ObligationPhasePlan:',
        'class ObligationPhaseAssessment:',
        'def bind_obligation_phase(',
        'def validate_obligation_phase_binding(',
        'def validate_obligation_phase_plan(',
        'def assess_obligation_phase_readiness(',
        '"calculus_state_schema_version": CALCULUS_STATE_SCHEMA_VERSION',
        '"obligation_identity": "EXISTING_OBLIGATION_ID_UNCHANGED_NO_NEW_OBLIGATION_IDENTITY"',
        '"binding_projection_id": OBLIGATION_BINDING_PROJECTION_ID',
        '"binding_projection": "VERSIONED_STABLE_REQUIREMENT_PROJECTION_HASHED_WITH_EXISTING_CALCULUS_CONTENT_HASH"',
        '"binding_projection_is_obligation_identity": False',
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
        "def content_hash(",
        "def obligation_fingerprint(",
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
        'def content_hash(',
        'class ObligationRecord:',
        'OBLIGATION_STATUSES = {',
        'OBLIGATION_TRANSITIONS = {',
        '"obligations": {},',
        '"obligation_edges": [],',
    ), "existing calculus model")
    require(calculus_public, (
        'from ._calculus_model import *',
        'from ._calculus_logic import *',
    ), "existing calculus public facade")
    if OBLIGATION_STATUSES != EXPECTED_OBLIGATION_STATUSES:
        fail(f"live obligation status vocabulary drifted: {sorted(OBLIGATION_STATUSES)}")
    if OBLIGATION_TRANSITIONS != EXPECTED_OBLIGATION_TRANSITIONS:
        fail(f"live obligation transition machine drifted: {OBLIGATION_TRANSITIONS}")
    if int(default_calculus_state().get("schema_version", -1)) != 1:
        fail("live calculus state schema_version is no longer 1")

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

    binding_schema = json.loads(text("schemas/obligation-phase-binding.schema.json"))
    plan_schema = json.loads(text("schemas/obligation-phase-plan.schema.json"))
    assessment_schema = json.loads(text("schemas/obligation-phase-assessment.schema.json"))
    for filename, schema, contract_id in (
        ("schemas/obligation-phase-binding.schema.json", binding_schema, "aasm.obligation.phase-binding.v1"),
        ("schemas/obligation-phase-plan.schema.json", plan_schema, "aasm.obligation.phase.v1"),
        ("schemas/obligation-phase-assessment.schema.json", assessment_schema, "aasm.obligation.phase-assessment.v1"),
    ):
        if schema.get("additionalProperties") is not False:
            fail(f"{filename} must be closed")
        serialized = json.dumps(schema, sort_keys=True)
        if contract_id not in serialized:
            fail(f"{filename} missing contract ID {contract_id}")
        if "RECOVERY" not in serialized and "assessment" not in filename:
            fail(f"{filename} missing RECOVERY phase vocabulary")
    binding_serialized = json.dumps(binding_schema, sort_keys=True)
    plan_serialized = json.dumps(plan_schema, sort_keys=True)
    if "obligation_semantic_fingerprint" not in binding_serialized or "obligation_semantic_fingerprint" not in plan_serialized:
        fail("phase binding schemas must carry obligation_semantic_fingerprint")
    if '"obligation_fingerprint"' in binding_serialized or '"obligation_fingerprint"' in plan_serialized:
        fail("stale claim of native obligation_fingerprint remains in phase binding schemas")

    for token in (
        "test_phase_vocabulary_order_and_recovery_orthogonality_are_exact",
        "test_binding_uses_exact_obligation_semantic_projection_scope_and_revision",
        "test_runtime_progress_changes_do_not_stale_binding_but_semantic_requirement_changes_do",
        "test_statement_activation_dependency_and_scope_changes_stale_phase_binding",
        "test_plan_requires_exactly_one_binding_for_every_existing_obligation",
        "test_forward_normal_dependency_is_valid_and_backward_normal_dependency_fails_closed",
        "test_dependency_record_and_edge_projection_must_agree_exactly",
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
