from __future__ import annotations

import json
from pathlib import Path

from aasm.effect_capability_use import EFFECT_CAPABILITY_USE_CONTRACT_ID, effect_capability_use_contract
from aasm.physical_control_fencing_runtime import (
    PHYSICAL_CONTROL_FENCING_CAPABILITIES,
    PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID,
    physical_control_fencing_runtime_contract,
)
from aasm.physical_preemption import AUTHORITY_PREEMPTION_CONTRACT_ID, authority_preemption_contract


ROOT=Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition: raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str,...]) -> None:
    text=path.read_text(encoding="utf-8")
    missing=[token for token in tokens if token not in text]
    require(not missing,f"{path}: missing physical-control-fencing tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str,...]) -> None:
    text=path.read_text(encoding="utf-8")
    present=[token for token in tokens if token in text]
    require(not present,f"{path}: PR-3E/F/G contains forbidden Effect integration tokens {present}")


def main() -> None:
    use=effect_capability_use_contract(); preempt=authority_preemption_contract(); runtime=physical_control_fencing_runtime_contract()
    require(use["contract_id"]==EFFECT_CAPABILITY_USE_CONTRACT_ID,"capability-use contract drift")
    require(use["role"]=="POINT_IN_TIME_STALE_COMMAND_FENCE_NOT_DURABLE_EFFECT_AUTHORIZATION","capability-use role drift")
    require(use["capability_identity"]=="EXACT_ID_AND_FINGERPRINT_REQUIRED","capability identity fence drift")
    require(use["lease_identity"]=="EXACT_ID_AND_FINGERPRINT_REQUIRED","lease identity fence drift")
    require(use["holder"]=="ACTOR_MUST_EQUAL_CURRENT_CAPABILITY_HOLDER","holder fence drift")
    require(use["numeric_parameters"]=="MUST_SATISFY_ALL_CURRENT_NAMED_CLOSED_BOUNDS","numeric-bound fence drift")
    require(use["numeric_units"]=="NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT","use fence overclaims unit semantics")
    require(use["epoch"]=="EXACT_CURRENT_AUTHORITY_EPOCH_REQUIRED","epoch fence drift")
    require(use["revocation_generation"]=="EXACT_CURRENT_EFFECTIVE_CAPABILITY_GENERATION_REQUIRED","generation fence drift")
    require(use["validation_grants_effect_authority"] is False,"use validation became effect authority")
    require(use["validation_is_reusable_authorization_token"] is False,"use validation became reusable authorization")
    require(use["required_recheck"]=="PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES","PR3H recheck requirement drift")
    require(use["effect_authorization_integration"]=="NOT_YET_PR3H","use fence integrated Effect authorization early")
    require(use["effect_dispatch"]=="NONE","use fence gained dispatch")

    require(preempt["contract_id"]==AUTHORITY_PREEMPTION_CONTRACT_ID,"preemption contract drift")
    require(preempt["identity_reference"]=="PREEMPTOR_MUST_BE_LISTED_BY_AUTHORITY_DOMAIN","preemptor identity boundary drift")
    require(preempt["identity_reference_grants_authority"] is False,"preemptor identity became authority")
    require(preempt["authorization"]=="EXISTING_SCOPED_PHYSICAL_AUTHORITY_PREEMPT_REQUIRED","preemption bypassed scoped authority")
    require(preempt["target"]=="EXACT_ACTIVE_AUTHORITY_LEASE_ID_FINGERPRINT_AND_EPOCH_REQUIRED","preemption target fence drift")
    require(preempt["effect"]=="CANONICAL_AUTHORITY_LEASE_REVOCATION_PLUS_PREEMPTION_EVIDENCE","preemption effect drift")
    require(preempt["epoch"]=="REQUIRED_NEXT_EPOCH_EQUALS_PREEMPTED_EPOCH_PLUS_ONE","preemption epoch drift")
    require(preempt["preemption_grants_new_effect_authority"] is False,"preemption grants new effect authority")
    require(preempt["parallel_authority_evaluator"]=="NONE","preemption introduced parallel authority evaluator")
    require(preempt["parallel_effect_lifecycle"]=="NONE","preemption introduced parallel effect lifecycle")
    require(preempt["effect_authorization_integration"]=="NOT_YET_PR3H","preemption integrated Effect authorization early")

    require(runtime["contract_id"]==PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID,"control-fencing runtime contract drift")
    require(runtime["durability"]=="EXISTING_AASM_EVIDENCE_EVENT_REPLAY","control-fencing introduced parallel persistence")
    require(runtime["authority"]=="EXISTING_AASM_SCOPED_AUTHORITY_ONLY","control-fencing bypassed scoped authority")
    require(runtime["use_validation"]=="POINT_IN_TIME_ONLY_REQUIRES_RECHECK_AT_PR3H_EFFECT_BOUNDARIES","use validation boundary drift")
    require(runtime["use_numeric_parameters"]=="EXACT_CAPABILITY_BOUND_NAME_SET_REQUIRED_FOUNDATION","numeric parameter exact-set boundary drift")
    require(runtime["preemption"]=="LISTED_PREEMPTOR_PLUS_SCOPED_PREEMPT_AUTHORITY","preemption dual-fence drift")
    require(runtime["preemption_effect"]=="EXISTING_AUTHORITY_LEASE_REVOCATION_REPRESENTATION","preemption bypassed canonical lease revocation")
    require(runtime["use_validation_grants_effect_authority"] is False,"runtime use validation became effect authority")
    require(runtime["preemption_grants_effect_authority"] is False,"runtime preemption grants effect authority")
    require(runtime["effect_authorization_integration"]=="NONE_PR3E_PR3F_PR3G_FOUNDATION","runtime integrated Effects before PR3H")
    require(runtime["effect_dispatch"]=="NONE","runtime gained Effect dispatch")
    require(runtime["machine_state_mutation"]=="NONE","runtime mutates machine state")
    require(runtime["parallel_authority_evaluator"]=="NONE","runtime parallel authority evaluator introduced")
    require(runtime["parallel_effect_lifecycle"]=="NONE","runtime parallel effect lifecycle introduced")
    require(runtime["capabilities"]==PHYSICAL_CONTROL_FENCING_CAPABILITIES,"control-fencing scoped capability registry drift")

    for filename,contract_id in (("effect-capability-use.schema.json",EFFECT_CAPABILITY_USE_CONTRACT_ID),("authority-preemption.schema.json",AUTHORITY_PREEMPTION_CONTRACT_ID)):
        schema=json.loads((ROOT/"schemas"/filename).read_text(encoding="utf-8"))
        require(schema["properties"]["contract_id"]["const"]==contract_id,f"schema drift: {filename}")

    require_tokens(ROOT/"src/aasm/physical_control_fencing_runtime.py",(
        'PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID = "aasm.physical.control-fencing.runtime.v1"',
        '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
        '"effect_authorization_integration": "NONE_PR3E_PR3F_PR3G_FOUNDATION"',
        "effect_capability_report(","authority_lease_report(","authority_domain_report(",
        'set(item.numeric_parameters) != set(capability.numeric_bounds)',
        'PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"]',
        '_AUTHORITY_LEASE_REVOCATION_RECORD',
        '_record_physical_authority_document(',
    ))
    forbid_tokens(ROOT/"src/aasm/physical_control_fencing_runtime.py",(
        "self.authorize_effect(","self.execute_effect(","self.reconcile_effect(",
        "EffectDispatchRequest","EffectOwnership","EffectReconciliation","bind_effect_ownership",
    ))
    require_tokens(ROOT/"tests/test_physical_control_fencing.py",(
        "test_use_fence_rejects_stale_identity_holder_epoch_generation_operation_bounds_scope_and_revision",
        "test_previously_valid_use_evidence_does_not_authorize_after_capability_revocation",
        "test_preemptor_reference_without_scoped_preempt_authority_is_denied",
        "test_scoped_preempt_authority_without_domain_preemptor_identity_is_denied",
        "test_semantic_preemption_uses_canonical_lease_revocation_invalidates_capability_and_allows_next_epoch",
        "test_sqlite_restart_reconstructs_use_and_preemption_and_exact_replay",
    ))
    print("physical control fencing preserves point-in-time stale-command checks, dual-authority preemption, canonical lease revocation, monotonic next epoch, and no Effect integration: PASS")


if __name__=="__main__": main()
