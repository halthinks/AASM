from __future__ import annotations

import json
from pathlib import Path

from aasm import public_api_contract, validate_public_api_contract
from aasm.external_machine_transition import (
    MACHINE_TRANSITION_CONTRACT_ID,
    machine_transition_contract,
)
from aasm.external_machine_transition_runtime import (
    MACHINE_TRANSITION_CAPABILITIES,
    MACHINE_TRANSITION_RUNTIME_CONTRACT_ID,
    machine_transition_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing machine-transition contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: PR-2B contains forbidden authorization/dispatch/ownership tokens {present}")


def main() -> None:
    semantic = machine_transition_contract()
    runtime = machine_transition_runtime_contract()
    require(semantic["contract_id"] == MACHINE_TRANSITION_CONTRACT_ID, "machine transition contract drift")
    require(semantic["expected_prestate"] == "EXACT_DURABLE_AUTHORITATIVE_STATE_CLAIMS_REQUIRED", "pre-state boundary drift")
    require(semantic["target_state"] == "EXACT_DURABLE_DESIRED_STATE_CLAIMS_REQUIRED", "target-state boundary drift")
    require(semantic["effect_proposal"] == "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY", "effect proposal path drift")
    require(semantic["effect_authorization"] == "EXISTING_AASM_AUTHORIZE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT", "transition gained authorization path")
    require(semantic["effect_dispatch"] == "EXISTING_AASM_EXECUTE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT", "transition gained dispatch path")
    require(semantic["parallel_dispatcher"] == "NONE", "parallel dispatcher introduced")
    require(semantic["parallel_effect_store"] == "NONE", "parallel effect store introduced")
    require(semantic["command_success_is_achievement"] is False, "command success became achievement")
    require(semantic["postcondition_verification"] == "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C", "PR-2B overclaims postconditions")
    require(semantic["transition_proposal_grants_effect_authority"] is False, "transition proposal gained effect authority")
    require(runtime["contract_id"] == MACHINE_TRANSITION_RUNTIME_CONTRACT_ID, "machine transition runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel transition persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel transition authority introduced")
    require(runtime["effect_proposal_path"] == "EXISTING_AASM_PROPOSE_EFFECT_ONLY", "runtime no longer uses existing propose_effect")
    require(runtime["effect_authorization"] == "NOT_PERFORMED_USE_EXISTING_AUTHORIZE_EFFECT", "runtime gained effect authorization")
    require(runtime["effect_dispatch"] == "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT", "runtime gained effect dispatch")
    require(runtime["effect_ownership"] == "NOT_CREATED_BY_THIS_RUNTIME", "runtime gained effect ownership")
    require(runtime["effect_reconciliation"] == "NOT_CREATED_BY_THIS_RUNTIME", "runtime gained effect reconciliation")
    require(runtime["transition_status_store"] == "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD", "parallel transition lifecycle introduced")
    require(runtime["parallel_dispatcher"] == "NONE", "runtime parallel dispatcher introduced")
    require(runtime["parallel_effect_store"] == "NONE", "runtime parallel effect store introduced")
    require(runtime["machine_state_mutation"] == "NONE", "transition proposal mutates core machine state")
    require(runtime["capabilities"] == MACHINE_TRANSITION_CAPABILITIES, "machine transition capability registry drift")

    schema = json.loads((ROOT / "schemas" / "machine-transition.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == MACHINE_TRANSITION_CONTRACT_ID, "machine transition schema drift")

    require_tokens(
        ROOT / "src/aasm/external_machine_transition.py",
        (
            'MACHINE_TRANSITION_CONTRACT_ID = "aasm.machine.transition.v1"',
            '"effect_proposal": "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY"',
            '"parallel_dispatcher": "NONE"',
            '"parallel_effect_store": "NONE"',
            '"command_success_is_achievement": False',
            '"postcondition_verification": "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/external_machine_transition_runtime.py",
        (
            'MACHINE_TRANSITION_RUNTIME_CONTRACT_ID = "aasm.machine.transition.runtime.v1"',
            '"effect_proposal_path": "EXISTING_AASM_PROPOSE_EFFECT_ONLY"',
            '"transition_status_store": "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD"',
            "self.propose_effect(",
            "EffectIntent.from_dict",
            "state_claim_report",
            "machine_binding_report",
            "_authorize_external_machine_action(",
        ),
    )
    # PR-2B deliberately reuses the PR-2A scoped-authority wrapper. Verify that
    # wrapper still terminates at the existing AASM scoped-authority evaluator.
    require_tokens(
        ROOT / "src/aasm/external_machine_runtime.py",
        (
            "def _authorize_external_machine_action(",
            "self.authorize_scoped_request(",
            "AuthorityRequest(",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/external_machine_transition_runtime.py",
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
        ROOT / "src/aasm/runtime_v56_foundation.py",
        ("MachineTransitionRuntimeMixin", "ExternalMachineRuntimeMixin", "V55FoundationEngine"),
    )
    require_tokens(
        ROOT / "tests/test_machine_transition.py",
        (
            "test_valid_transition_creates_only_existing_proposed_effect_intent_with_exact_claim_conditions",
            "test_transition_proposal_does_not_grant_effect_authority_and_existing_authorize_effect_remains_authority_boundary",
            "test_transition_proposal_is_idempotent_and_does_not_duplicate_effect_or_transition",
            "test_sqlite_restart_reconstructs_machine_transition_and_existing_effect_binding",
        ),
    )

    public = validate_public_api_contract()
    require(public["valid"], f"active public contract invalid: {public['errors']}")
    contract = public_api_contract()
    require(contract["contract_version"] == "0.32.4", "active adoption contract did not advance for PR-2B")
    require(contract["machine_transition"]["runtime"]["effect_proposal_path"] == "EXISTING_AASM_PROPOSE_EFFECT_ONLY", "public transition proposal path drift")
    require(contract["machine_transition"]["runtime"]["effect_dispatch"] == "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT", "public PR-2B gained dispatch")
    require(contract["machine_transition"]["runtime"]["effect_ownership"] == "NOT_CREATED_BY_THIS_RUNTIME", "public PR-2B gained ownership")
    require(contract["machine_transition"]["runtime"]["transition_status_store"] == "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD", "public parallel transition status introduced")

    print("machine transition uses existing EffectIntent proposal path and preserves no-authorization/no-dispatch boundary: PASS")


if __name__ == "__main__":
    main()
