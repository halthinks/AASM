#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} is missing required S5.1 refinement-runtime tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.1 refinement-runtime firewalls: {found}")


def main() -> None:
    runtime = "src/aasm/refinement_runtime.py"
    tests = "tests/test_refinement_runtime.py"
    workflow = ".github/workflows/refinement.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        runtime,
        "class RefinementRuntimeMixin",
        "project_refinement_evidence",
        "REFINEMENT_APPLY_CAPABILITY = \"problem.refinement.apply\"",
        "authorize_scoped_request(",
        "commit_problem_revision_transition(",
        "resume_problem_revision_impacts(",
        "DUPLICATE_SEMANTIC_REFINEMENT_APPLICATION",
        "refinement producer/evaluator cannot directly apply its own delta",
        "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "EXISTING_AASM_SCOPED_AUTHORITY_DECISION_REQUIRED",
        "EXISTING_AASM_SEMANTIC_EVOLUTION_RUNTIME_ONLY",
        "EXISTING_AASM_SEMANTIC_DEPENDENCY_RUNTIME_ONLY",
        "\"parallel_refinement_store\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        runtime,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "class RefinementStore",
        "class ProblemRevisionStore",
        "apply_problem_delta_directly",
    )

    require_tokens(
        tests,
        "test_governed_refinement_commits_through_existing_problem_revision_transition",
        "test_producer_cannot_apply_its_own_delta_even_before_scoped_authority_is_considered",
        "test_application_without_existing_scoped_authority_fails_closed_without_revision_mutation",
        "test_exact_application_is_idempotent_but_conflicting_repeat_is_blocked_by_application_key",
        "test_truth_changing_refinement_must_complete_existing_truth_maintenance_before_application_record",
        "test_loop_termination_is_durable_and_bound_to_current_problem_head",
    )

    require_tokens(
        workflow,
        "src/aasm/refinement_runtime.py",
        "scripts/check_refinement_runtime_contracts.py",
        "tests/test_refinement_runtime.py",
    )

    if "refinement_runtime" in text(public):
        raise SystemExit(
            "S5.1 refinement runtime must remain pre-admission and absent from the active public root"
        )

    print("S5.1 durable governed refinement runtime contracts: PASS")


if __name__ == "__main__":
    main()
