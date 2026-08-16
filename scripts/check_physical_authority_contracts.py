from __future__ import annotations

import json
from pathlib import Path

from aasm.physical_authority import (
    AUTHORITY_DOMAIN_CONTRACT_ID,
    AUTHORITY_LEASE_CONTRACT_ID,
    physical_authority_contract,
)
from aasm.physical_authority_runtime import (
    PHYSICAL_AUTHORITY_CAPABILITIES,
    PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID,
    physical_authority_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing physical-authority contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: PR-3A/3B contains forbidden effect/parallel-authority tokens {present}")


def main() -> None:
    semantic = physical_authority_contract()
    runtime = physical_authority_runtime_contract()
    require(semantic["domain_contract_id"] == AUTHORITY_DOMAIN_CONTRACT_ID, "authority-domain contract drift")
    require(semantic["lease_contract_id"] == AUTHORITY_LEASE_CONTRACT_ID, "authority-lease contract drift")
    require(semantic["domain_role"] == "BOUNDED_EFFECT_AUTHORITY_NAMESPACE_NOT_AUTHORITY_GRANT", "domain became authority grant")
    require(semantic["lease_role"] == "EXCLUSIVE_TIME_BOUNDED_DOMAIN_HOLDER_NOT_EFFECT_PERMISSION_BY_EXISTENCE", "lease became effect permission")
    require(semantic["lease_exclusivity"] == "AT_MOST_ONE_ACTIVE_LEASE_PER_DOMAIN", "lease exclusivity drift")
    require(semantic["authority_epoch"] == "STRICTLY_MONOTONIC_PER_DOMAIN", "authority epoch drift")
    require(semantic["resource_availability_grants_authority"] is False, "resources became authority")
    require(semantic["fact_authority_grants_effect_authority"] is False, "fact authority became effect authority")
    require(semantic["domain_existence_grants_effect_authority"] is False, "domain existence became effect authority")
    require(semantic["lease_existence_grants_effect_authority"] is False, "lease existence became effect authority")
    require(semantic["parallel_authority_evaluator"] == "NONE", "parallel authority evaluator introduced")
    require(semantic["parallel_effect_lifecycle"] == "NONE", "parallel effect lifecycle introduced")
    require(semantic["effect_authorization_integration"] == "NOT_YET_PR3H", "PR-3A/3B integrated effect authorization early")
    require(semantic["bounded_effect_capability"] == "RESERVED_PR3C_PR3D", "PR-3A/3B overclaims bounded effect capability")
    require(semantic["semantic_preemption"] == "RESERVED_PR3G", "PR-3A/3B overclaims preemption")

    require(runtime["contract_id"] == PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID, "physical-authority runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel physical-authority persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel authority evaluator introduced")
    require(runtime["lease_exclusivity"] == "NON_OVERLAPPING_EFFECTIVE_INTERVALS_PER_DOMAIN", "runtime lease exclusivity drift")
    require(runtime["authority_epoch"] == "EXPLICIT_NEXT_MONOTONIC_EPOCH_REQUIRED", "runtime epoch boundary drift")
    require(runtime["preemptor_reference_grants_authority"] is False, "preemptor reference became authority")
    require(runtime["domain_existence_grants_effect_authority"] is False, "runtime domain became effect authority")
    require(runtime["lease_existence_grants_effect_authority"] is False, "runtime lease became effect authority")
    require(runtime["effect_authorization_integration"] == "NONE_PR3A_PR3B_FOUNDATION", "runtime integrated effect authorization early")
    require(runtime["effect_dispatch"] == "NONE", "physical-authority foundation gained dispatch")
    require(runtime["machine_state_mutation"] == "NONE", "physical-authority foundation mutates machine state")
    require(runtime["parallel_authority_evaluator"] == "NONE", "runtime parallel authority evaluator introduced")
    require(runtime["parallel_effect_lifecycle"] == "NONE", "runtime parallel effect lifecycle introduced")
    require(runtime["capabilities"] == PHYSICAL_AUTHORITY_CAPABILITIES, "physical-authority capability registry drift")

    for filename, contract_id in (
        ("authority-domain.schema.json", AUTHORITY_DOMAIN_CONTRACT_ID),
        ("authority-lease.schema.json", AUTHORITY_LEASE_CONTRACT_ID),
    ):
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(schema["properties"]["contract_id"]["const"] == contract_id, f"physical-authority schema drift: {filename}")

    require_tokens(
        ROOT / "src/aasm/physical_authority.py",
        (
            'AUTHORITY_DOMAIN_CONTRACT_ID = "aasm.authority.domain.v1"',
            'AUTHORITY_LEASE_CONTRACT_ID = "aasm.authority.lease.v1"',
            '"lease_exclusivity": "AT_MOST_ONE_ACTIVE_LEASE_PER_DOMAIN"',
            '"authority_epoch": "STRICTLY_MONOTONIC_PER_DOMAIN"',
            '"lease_existence_grants_effect_authority": False',
            '"effect_authorization_integration": "NOT_YET_PR3H"',
            '"semantic_preemption": "RESERVED_PR3G"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/physical_authority_runtime.py",
        (
            'PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.physical.authority.runtime.v1"',
            '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
            '"effect_authorization_integration": "NONE_PR3A_PR3B_FOUNDATION"',
            "self.authorize_scoped_request(",
            "AuthorityRequest(",
            "add_evidence_guarded",
            "expected_epoch = max_epoch + 1",
            "_intervals_overlap(",
            "revocation_generation",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/physical_authority_runtime.py",
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
        ROOT / "tests/test_physical_authority.py",
        (
            "test_authority_lease_epoch_is_strictly_monotonic_and_intervals_cannot_overlap",
            "test_revocation_is_append_only_closes_effective_interval_and_next_epoch_can_begin",
            "test_authority_domain_or_lease_never_grants_existing_effect_authority",
            "test_physical_authority_records_do_not_mutate_core_machine_state",
            "test_sqlite_restart_reconstructs_domains_leases_revocations_and_exact_replay",
        ),
    )

    print("physical authority domain/lease foundation preserves scoped authority, exclusivity, epochs, revocation, and no-effect-authority boundary: PASS")


if __name__ == "__main__":
    main()
