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
        raise SystemExit(f"{path} is missing required S5.3 verification-assurance tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.3 verification-assurance firewalls: {found}")


def main() -> None:
    module = "src/aasm/verification_planning_assurance.py"
    tests = "tests/test_verification_planning_assurance.py"
    workflow = ".github/workflows/verification-planning.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        module,
        "VERIFICATION_PLANNING_ASSURANCE_CONTRACT_ID = \"aasm.verification.planning.assurance.v1\"",
        "def assure_verification_planning_inputs(",
        "def project_verification_debt_assured(",
        "APPLICABILITY_EVIDENCE_TYPE_MISMATCH",
        "APPLICABILITY_ASSESSMENT_EVIDENCE_REQUIRED",
        "STALE_APPLICABILITY_ASSESSMENT_EVIDENCE",
        "STALE_VERIFICATION_PLAN_SUPPORT",
        "DOWNGRADE_TO_INDETERMINATE_FOR_DEBT_PROJECTION",
        "FAIL_CLOSED_REPLAN_REQUIRED",
        "\"truth_authority\": \"NONE\"",
        "\"obligation_mutation\": \"NONE\"",
        "\"evidence_mutation\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        module,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "reserve_candidate_resources(",
        "transition_obligation(",
        "commit_problem_revision_transition(",
    )
    require_tokens(
        tests,
        "test_applicability_cannot_relabel_existing_evidence_kind_to_clear_debt",
        "test_applicable_claim_requires_assessment_evidence_provenance",
        "test_stale_applicability_assessment_is_downgraded_not_trusted",
        "test_stale_verifier_profile_support_requires_replan_instead_of_using_assignment",
        "test_invalidated_result_evidence_remains_verification_debt_not_input_failure",
    )
    require_tokens(
        workflow,
        "src/aasm/verification_planning_assurance.py",
        "scripts/check_verification_planning_assurance_contracts.py",
        "tests/test_verification_planning_assurance.py",
    )
    if "verification_planning_assurance" in text(public):
        raise SystemExit("S5.3 verification assurance must remain absent from the active public root")
    print("S5.3 verification planning cross-history assurance contracts: PASS")


if __name__ == "__main__":
    main()
