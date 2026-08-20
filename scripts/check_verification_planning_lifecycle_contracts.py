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
        raise SystemExit(f"{path} is missing required S5.3 verification-lifecycle tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.3 verification-lifecycle firewalls: {found}")


def main() -> None:
    module = "src/aasm/verification_planning_lifecycle.py"
    tests = "tests/test_verification_planning_lifecycle.py"
    workflow = ".github/workflows/verification-planning.yml"

    require_tokens(
        module,
        "VERIFICATION_PLAN_LIFECYCLE_CONTRACT_ID = \"aasm.verification.plan.lifecycle.v1\"",
        "def validate_verification_plan_current_applicability(",
        "def project_verification_debt_current(",
        "def project_verification_debt_current_assured(",
        "IMMUTABLE_EXACT_CALCULUS_STATE_FINGERPRINT",
        "REVALIDATE_CANONICAL_OBLIGATION_SEMANTICS_NOT_WHOLE_STATE_EQUALITY",
        "CURRENT_PLAN_MISSING_NEW_VERIFICATION_OBLIGATIONS",
        "CURRENT_PLAN_OBLIGATION_SEMANTIC_DRIFT",
        "VERIFICATION_PLAN_CURRENT_SEMANTIC_DRIFT_REPLAN_REQUIRED",
        "ORIGINAL_PLAN_ID_AND_FINGERPRINT_RETAINED",
        "\"obligation_mutation\": \"NONE\"",
        "\"truth_authority\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        module,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "transition_obligation(",
        "commit_problem_revision_transition(",
        "replace(plan",
    )
    require_tokens(
        tests,
        "test_evidence_attachment_changes_state_fingerprint_but_does_not_semantically_invalidate_plan",
        "test_current_debt_can_clear_after_result_evidence_attaches_without_rewriting_plan",
        "test_satisfied_obligation_may_leave_current_debt_without_rewriting_original_plan",
        "test_new_unplanned_verification_obligation_forces_replan",
        "test_required_evidence_semantic_drift_forces_replan",
    )
    require_tokens(
        workflow,
        "src/aasm/verification_planning_lifecycle.py",
        "scripts/check_verification_planning_lifecycle_contracts.py",
        "tests/test_verification_planning_lifecycle.py",
    )
    print("S5.3 verification plan lifecycle/debt contracts: PASS")


if __name__ == "__main__":
    main()
