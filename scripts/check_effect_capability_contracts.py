from __future__ import annotations

import json
from pathlib import Path

from aasm.effect_capability import EFFECT_CAPABILITY_CONTRACT_ID, effect_capability_contract
from aasm.effect_capability_runtime import (
    EFFECT_CAPABILITY_CAPABILITIES,
    EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID,
    effect_capability_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing effect-capability contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: PR-3C/3D contains forbidden effect-integration/parallel-authority tokens {present}")


def main() -> None:
    semantic = effect_capability_contract()
    runtime = effect_capability_runtime_contract()
    require(semantic["contract_id"] == EFFECT_CAPABILITY_CONTRACT_ID, "effect capability contract drift")
    require(semantic["authority_source"] == "EXISTING_ACTIVE_AUTHORITY_LEASE_REQUIRED", "capability authority-source drift")
    require(semantic["root_issuer"] == "ACTIVE_AUTHORITY_LEASE_HOLDER_ONLY", "root issuer boundary drift")
    require(semantic["operation_bound"] == "CAPABILITY_OPERATIONS_SUBSET_OF_LEASE_OR_PARENT", "operation non-amplification drift")
    require(semantic["numeric_bound"] == "NAMED_CLOSED_NUMERIC_INTERVALS_ONLY", "numeric bound semantics drift")
    require(semantic["numeric_units"] == "NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT", "PR-3C/3D overclaims unit semantics")
    require(semantic["validity_bound"] == "CAPABILITY_INTERVAL_SUBSET_OF_LEASE_OR_PARENT", "validity non-amplification drift")
    require(semantic["scope_bound"] == "EXACT_DOMAIN_LEASE_SCOPE_FOUNDATION", "scope boundary drift")
    require(semantic["epoch_bound"] == "EXACT_AUTHORITY_LEASE_EPOCH", "epoch boundary drift")
    require(semantic["delegation"] == "CHILD_RIGHTS_MUST_BE_SUBSET_AND_DEPTH_MUST_DECREASE", "delegation non-amplification drift")
    require(semantic["parent_revocation"] == "CHILD_CAPTURES_PARENT_FINGERPRINT_AND_REVOCATION_GENERATION", "parent revocation fence drift")
    require(semantic["capability_existence_grants_effect_authority"] is False, "capability existence became effect authority")
    require(semantic["parallel_authority_evaluator"] == "NONE", "parallel authority evaluator introduced")
    require(semantic["parallel_effect_lifecycle"] == "NONE", "parallel effect lifecycle introduced")
    require(semantic["effect_authorization_integration"] == "NOT_YET_PR3H", "PR-3C/3D integrated effect authorization early")
    require(semantic["semantic_preemption"] == "RESERVED_PR3G", "PR-3C/3D overclaims semantic preemption")

    require(runtime["contract_id"] == EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID, "effect capability runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel effect-capability persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "effect capability bypassed scoped authority")
    require(runtime["lease_source"] == "EXISTING_PR3A_PR3B_AUTHORITY_LEASE_ONLY", "effect capability bypassed authority lease")
    require(runtime["root_issue"] == "ACTIVE_LEASE_HOLDER_PLUS_SCOPED_ISSUE_AUTHORITY_REQUIRED", "root issue authority drift")
    require(runtime["delegation"] == "ACTIVE_PARENT_HOLDER_PLUS_SCOPED_DELEGATE_AUTHORITY_REQUIRED", "delegation authority drift")
    require(runtime["non_amplification"] == "OPERATIONS_BOUNDS_VALIDITY_SCOPE_REVISION_EPOCH_AND_DEPTH_FAIL_CLOSED", "runtime non-amplification drift")
    require(runtime["revocation"] == "APPEND_ONLY_GENERATION_INVALIDATES_CAPABILITY_AND_DESCENDANTS", "runtime revocation drift")
    require(runtime["capability_existence_grants_effect_authority"] is False, "runtime capability existence became effect authority")
    require(runtime["effect_authorization_integration"] == "NONE_PR3C_PR3D_FOUNDATION", "runtime integrated effect authorization early")
    require(runtime["effect_dispatch"] == "NONE", "effect capability runtime gained dispatch")
    require(runtime["machine_state_mutation"] == "NONE", "effect capability runtime mutates machine state")
    require(runtime["parallel_authority_evaluator"] == "NONE", "runtime parallel authority evaluator introduced")
    require(runtime["parallel_effect_lifecycle"] == "NONE", "runtime parallel effect lifecycle introduced")
    require(runtime["capabilities"] == EFFECT_CAPABILITY_CAPABILITIES, "effect capability scoped-capability registry drift")

    schema = json.loads((ROOT / "schemas" / "effect-capability.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == EFFECT_CAPABILITY_CONTRACT_ID, "effect capability schema drift")

    require_tokens(
        ROOT / "src/aasm/effect_capability.py",
        (
            'EFFECT_CAPABILITY_CONTRACT_ID = "aasm.effect.capability.v1"',
            "class NumericInterval",
            "def numeric_bounds_subset(",
            '"numeric_units": "NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT"',
            '"delegation": "CHILD_RIGHTS_MUST_BE_SUBSET_AND_DEPTH_MUST_DECREASE"',
            '"capability_existence_grants_effect_authority": False',
            '"effect_authorization_integration": "NOT_YET_PR3H"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/effect_capability_runtime.py",
        (
            'EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID = "aasm.effect.capability.runtime.v1"',
            '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
            '"effect_authorization_integration": "NONE_PR3C_PR3D_FOUNDATION"',
            "self.authorize_scoped_request(",
            "authority_lease_report(",
            "authority_epoch",
            "numeric_bounds_subset(",
            "parent_revocation_generation",
            "remaining_delegation_depth",
            "add_evidence_guarded",
        ),
    )
    require_tokens(
        ROOT / "src/aasm/effect_capability_revocation_guard.py",
        (
            "float(at_time) >= float(revocation[\"revoked_at\"])",
            'result["effective_revocation_generation"] = effective_generation',
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/effect_capability_runtime.py",
        (
            "self.authorize_effect(",
            "self.execute_effect(",
            "self.reconcile_effect(",
            "EffectDispatchRequest",
            "EffectOwnership",
            "EffectReconciliation",
            "bind_effect_ownership",
        ),
    )
    require_tokens(
        ROOT / "tests/test_effect_capability.py",
        (
            "test_delegation_rejects_operation_bound_validity_scope_revision_epoch_and_depth_amplification",
            "test_parent_revocation_generation_fences_descendants_at_revocation_time_not_before",
            "test_authority_lease_revocation_invalidates_capability_without_rewriting_capability_history",
            "test_effect_capability_existence_still_does_not_grant_existing_effect_authority",
            "test_sqlite_restart_reconstructs_capability_tree_revocation_and_exact_replay",
        ),
    )

    print("bounded effect capability foundation preserves lease/epoch/revision/scope/operation/bounds/delegation/revocation non-amplification and no-effect-authority boundary: PASS")


if __name__ == "__main__":
    main()
