#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} is missing required S5.3 verification-planning tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.3 verification-planning firewalls: {found}")


def main() -> None:
    module = "src/aasm/verification_planning.py"
    tests = "tests/test_verification_planning_foundation.py"
    workflow = ".github/workflows/verification-planning.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        module,
        "VERIFICATION_PLAN_CONTRACT_ID = \"aasm.verification.plan.v1\"",
        "VERIFICATION_DEBT_CONTRACT_ID = \"aasm.verification.debt.v1\"",
        "class VerifierCapabilityProfile",
        "CapabilityContract",
        "capability.capability_type != \"VERIFIER\"",
        "class VerificationPlan",
        "class VerificationDebtProjection",
        "def validate_verification_plan(",
        "def project_verification_debt(",
        "PLAN_OMITS_CANONICAL_VERIFICATION_OBLIGATIONS",
        "REQUIREMENT_WEAKENS_OR_ALTERS_CANONICAL_EVIDENCE_TYPES",
        "EVIDENCE_APPLICABILITY_UNASSESSED",
        "STALE_EVIDENCE",
        "OPAQUE_NAMED_GRADE_EXACT_ACCEPTABILITY_NO_IMPLICIT_ORDERING",
        "DECLARATIVE_CLAIMS_NOT_PROOF_AUTHORITY",
        "\"verifier_execution\": \"NONE\"",
        "\"resource_reservation\": \"NONE\"",
        "\"fact_authority\": \"NONE\"",
        "\"debt_scalar_score\": \"NONE\"",
        "\"parallel_obligation_graph\": \"NONE\"",
        "\"parallel_truth_plane\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        module,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "reserve_candidate_resources(",
        "commit_problem_revision_transition(",
        "transition_obligation(",
        "class VerificationDebtStore",
        "class VerificationExecutor",
    )
    require_tokens(
        tests,
        "test_plan_cannot_omit_a_canonical_verification_obligation",
        "test_plan_cannot_weaken_canonical_required_evidence_types",
        "test_evidence_grades_have_no_implicit_ordering",
        "test_stale_evidence_remains_debt_and_cannot_clear_obligation",
        "test_terminal_unresolved_verification_obligation_remains_visible_debt",
        "test_satisfied_existing_obligation_leaves_verification_debt_projection",
    )
    for schema in ("schemas/verification-plan.schema.json", "schemas/verification-debt.schema.json"):
        json.loads(text(schema))
    require_tokens(
        workflow,
        "src/aasm/verification_planning.py",
        "scripts/check_verification_planning_contracts.py",
        "tests/test_verification_planning_foundation.py",
        "aasm/verification-planning",
    )
    if "verification_planning" in text(public):
        raise SystemExit("S5.3 verification planning foundation must remain absent from the active public root")
    print("S5.3 verification plan/debt pre-admission contracts: PASS")


if __name__ == "__main__":
    main()
