from __future__ import annotations

import json
from pathlib import Path

from aasm import public_api_contract, validate_public_api_contract
from aasm.external_machine_postcondition import (
    MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID,
    machine_postcondition_verification_contract,
)
from aasm.external_machine_postcondition_runtime import (
    MACHINE_POSTCONDITION_CAPABILITIES,
    MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID,
    machine_postcondition_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing machine-postcondition contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: PR-2C contains forbidden authority/effect-mutation tokens {present}")


def main() -> None:
    semantic = machine_postcondition_verification_contract()
    runtime = machine_postcondition_runtime_contract()
    require(semantic["contract_id"] == MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID, "machine postcondition contract drift")
    require(semantic["effect_status_requirement"] == "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED", "effect status boundary drift")
    require(semantic["unknown_effect"] == "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION", "UNKNOWN no longer routes to existing reconciliation")
    require(semantic["target_source"] == "PR2B_DURABLE_DESIRED_STATE_CLAIMS", "target source drift")
    require(semantic["achieved_source"] == "PR1_DURABLE_AUTHORITATIVE_STATE_CLAIMS_ONLY", "achieved source drift")
    require(semantic["observation_correlation"] == "PR2A_MACHINE_STATE_OBSERVATION_CORRELATION_ID_MUST_EQUAL_EXISTING_EFFECT_EXECUTION_ID", "execution correlation boundary drift")
    require(semantic["comparison"] == "EXACT_CANONICAL_VALUE_EQUALITY_ONLY_NO_TOLERANCE_IN_THIS_FOUNDATION", "comparison overclaim detected")
    require(semantic["effect_success_is_achievement"] is False, "effect success became achievement")
    require(semantic["verification_mints_fact_authority"] is False, "verification gained fact-authority minting")
    require(semantic["verification_mints_state_claim"] is False, "verification gained state-claim minting")
    require(semantic["verification_mutates_effect_outcome"] is False, "verification mutates effect outcome")
    require(semantic["verification_mutates_machine_state"] is False, "verification mutates machine state")
    require(semantic["verification_grants_effect_authority"] is False, "verification gained effect authority")
    require(semantic["parallel_truth_table"] == "NONE", "parallel truth table introduced")
    require(semantic["parallel_effect_lifecycle"] == "NONE", "parallel effect lifecycle introduced")

    require(runtime["contract_id"] == MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID, "machine postcondition runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel postcondition persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel postcondition authority evaluator introduced")
    require(runtime["effect_source"] == "EXISTING_AASM_EFFECT_RECORD_ONLY", "effect source bypassed existing effect record")
    require(runtime["transition_source"] == "EXISTING_PR2B_MACHINE_TRANSITION_ONLY", "transition source bypassed PR-2B")
    require(runtime["achieved_source"] == "EXISTING_PR1_AUTHORITATIVE_STATE_CLAIMS_ONLY", "runtime achieved source drift")
    require(runtime["observation_source"] == "EXISTING_PR2A_MACHINE_STATE_OBSERVATIONS_ONLY", "runtime observation source drift")
    require(runtime["effect_status_mutation"] == "NONE", "runtime mutates effect status")
    require(runtime["state_claim_creation"] == "NONE", "runtime creates state claims")
    require(runtime["fact_authority_creation"] == "NONE", "runtime creates fact authority")
    require(runtime["machine_state_mutation"] == "NONE", "runtime mutates machine state")
    require(runtime["effect_authority"] == "NONE", "runtime gained effect authority")
    require(runtime["parallel_truth_table"] == "NONE", "runtime parallel truth table introduced")
    require(runtime["parallel_effect_lifecycle"] == "NONE", "runtime parallel effect lifecycle introduced")
    require(runtime["capabilities"] == MACHINE_POSTCONDITION_CAPABILITIES, "postcondition capability registry drift")

    schema = json.loads((ROOT / "schemas" / "machine-postcondition-verification.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID, "machine postcondition schema drift")

    require_tokens(
        ROOT / "src/aasm/external_machine_postcondition.py",
        (
            'MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID = "aasm.machine.postcondition-verification.v1"',
            '"effect_success_is_achievement": False',
            '"verification_mints_fact_authority": False',
            '"verification_mints_state_claim": False',
            '"verification_mutates_effect_outcome": False',
            '"parallel_truth_table": "NONE"',
            '"freshness_semantics": "NOT_YET_CLAIMED_PR4"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/external_machine_postcondition_runtime.py",
        (
            'MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID = "aasm.machine.postcondition-verification.runtime.v1"',
            '"effect_source": "EXISTING_AASM_EFFECT_RECORD_ONLY"',
            '"state_claim_creation": "NONE"',
            '"fact_authority_creation": "NONE"',
            '"effect_status_mutation": "NONE"',
            "self.store.load_effect(",
            "machine_transition_report",
            "machine_state_observation_report",
            "state_claim_report",
            "_authorize_external_machine_action(",
            "add_evidence_guarded",
        ),
    )
    require_tokens(
        ROOT / "src/aasm/external_machine_postcondition_execution_correlation.py",
        (
            "effect.execution_id",
            "observation.correlation_id != execution_id",
            "super().verify_machine_transition_postconditions(",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/external_machine_postcondition_runtime.py",
        (
            "record_state_claim(",
            "register_fact_authority(",
            "revoke_fact_authority(",
            "authorize_effect(",
            "execute_effect(",
            "reconcile_effect(",
            "EffectDispatchRequest",
            "EffectOwnership",
            "EffectReconciliation",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/external_machine_postcondition_execution_correlation.py",
        (
            "record_state_claim(",
            "register_fact_authority(",
            "authorize_effect(",
            "execute_effect(",
            "reconcile_effect(",
        ),
    )
    require_tokens(
        ROOT / "tests/test_machine_postcondition.py",
        (
            "test_succeeded_effect_alone_is_insufficient_without_correlated_authoritative_observation",
            "test_correlated_observation_without_authoritative_admission_cannot_verify",
            "test_authoritative_claim_must_derive_from_supplied_correlated_observation",
            "test_exact_matching_authoritative_state_verifies_without_mutating_effect_truth_or_core_state",
            "test_exact_mismatch_is_durable_evidence_not_effect_failure_or_state_rewrite",
            "test_postcondition_verification_is_idempotent_and_sqlite_replay_safe",
        ),
    )

    public = validate_public_api_contract()
    require(public["valid"], f"active dependency public contract invalid: {public['errors']}")
    contract = public_api_contract()
    require(contract["contract_version"] == "0.32.4", "PR-2C foundation expected qualified PR-2B adoption 0.32.4")
    require("machine_transition" in contract, "PR-2B machine transition missing from active dependency surface")
    require(contract["machine_transition"]["runtime"]["effect_dispatch"] == "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT", "PR-2B dependency boundary drift")

    print("machine postcondition verifier uses existing effect + PR-1/PR-2A/PR-2B evidence and cannot mint authority or mutate effect truth: PASS")


if __name__ == "__main__":
    main()
