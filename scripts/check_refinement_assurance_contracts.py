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
        raise SystemExit(f"{path} is missing required S5.1 assurance tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.1 assurance firewalls: {found}")


def main() -> None:
    assurance = "src/aasm/refinement_runtime_assurance.py"
    tests = "tests/test_refinement_runtime_assurance.py"
    workflow = ".github/workflows/refinement.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        assurance,
        "class RefinementRuntimeAssuranceMixin",
        "assure_refinement_projection",
        "PROPOSAL_BASE_REVISION_FINGERPRINT_MISMATCH",
        "APPLICATION_TRANSITION_AUTHORITY_PRINCIPAL_MISMATCH",
        "APPLICATION_TRANSITION_AUTHORITY_CLASS_INVALID",
        "APPLICATION_TRUTH_IMPACT_PROVENANCE_MISMATCH",
        "TERMINATION_HEAD_REVISION_FINGERPRINT_MISMATCH",
        "STALE_REFINEMENT_VALIDATION_EVIDENCE",
        "INVALIDATED_SUPPORT_DOES_NOT_RETROACTIVELY_ERASE_COMMITTED_APPLICATION",
        "\"parallel_store\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        assurance,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "class RefinementStore",
        "class ProblemRevisionStore",
        "class AuthorityStore",
        "apply_problem_delta_directly",
    )

    require_tokens(
        tests,
        "test_forged_proposal_base_fingerprint_is_rejected_by_cross_history_assurance",
        "test_application_actor_must_match_authority_that_committed_canonical_transition",
        "test_stale_validation_support_cannot_authorize_a_new_revision_transition",
        "test_stale_validation_does_not_retroactively_erase_exact_committed_retry",
        "test_termination_fingerprints_must_match_canonical_revision_history",
    )
    require_tokens(
        workflow,
        "src/aasm/refinement_runtime_assurance.py",
        "scripts/check_refinement_assurance_contracts.py",
        "tests/test_refinement_runtime_assurance.py",
    )
    if "refinement_runtime_assurance" in text(public):
        raise SystemExit("S5.1 assurance must remain absent from the active public root")

    print("S5.1 governed refinement cross-history assurance contracts: PASS")


if __name__ == "__main__":
    main()
