from __future__ import annotations

import json
from pathlib import Path

from aasm import public_api_contract, validate_public_api_contract
from aasm.external_machine import (
    MACHINE_BINDING_CONTRACT_ID,
    MACHINE_STATE_OBSERVATION_CONTRACT_ID,
    external_machine_contract,
)
from aasm.external_machine_runtime import (
    EXTERNAL_MACHINE_CAPABILITIES,
    EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID,
    external_machine_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing external-machine contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: PR-2A contains forbidden dispatch/authority tokens {present}")


def main() -> None:
    semantic = external_machine_contract()
    runtime = external_machine_runtime_contract()
    require(semantic["binding_contract_id"] == MACHINE_BINDING_CONTRACT_ID, "machine binding contract drift")
    require(semantic["state_observation_contract_id"] == MACHINE_STATE_OBSERVATION_CONTRACT_ID, "machine observation contract drift")
    require(semantic["binding_role"] == "REFERENCE_AND_CORRELATION_ONLY_NOT_EXTERNAL_STATE_COPY", "machine binding became truth copy")
    require(semantic["binding_grants_fact_authority"] is False, "machine binding gained fact authority")
    require(semantic["binding_grants_effect_authority"] is False, "machine binding gained effect authority")
    require(semantic["capability_reference_grants_authority"] is False, "capability reference gained authority")
    require(semantic["external_state_table"] == "NONE", "parallel external state table introduced")
    require(semantic["executor_invocation"] == "NONE_BY_THIS_FOUNDATION", "PR-2A invokes executor")
    require(semantic["postcondition_achievement_claim"] == "NOT_YET_CLAIMED_PR2C", "PR-2A overclaims postcondition achievement")
    require(runtime["contract_id"] == EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID, "external machine runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel external-machine persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel external-machine authority evaluator introduced")
    require(runtime["state_observation_source"] == "EXISTING_PR1_DURABLE_OBSERVED_STATE_CLAIM", "external observation bypassed PR-1")
    require(runtime["external_state_table"] == "NONE", "runtime introduced external state table")
    require(runtime["effect_dispatch"] == "NONE", "runtime gained effect dispatch")
    require(runtime["executor_invocation"] == "NONE", "runtime gained executor invocation")
    require(runtime["machine_state_mutation"] == "NONE", "runtime mutates core machine state")
    require(runtime["binding_grants_fact_authority"] is False, "runtime binding gained fact authority")
    require(runtime["binding_grants_effect_authority"] is False, "runtime binding gained effect authority")
    require(runtime["capabilities"] == EXTERNAL_MACHINE_CAPABILITIES, "external-machine capability registry drift")

    for filename, contract_id in (
        ("machine-binding.schema.json", MACHINE_BINDING_CONTRACT_ID),
        ("machine-state-observation.schema.json", MACHINE_STATE_OBSERVATION_CONTRACT_ID),
    ):
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    require_tokens(
        ROOT / "src/aasm/external_machine.py",
        (
            'MACHINE_BINDING_CONTRACT_ID = "aasm.machine.binding.v1"',
            'MACHINE_STATE_OBSERVATION_CONTRACT_ID = "aasm.machine.state-observation.v1"',
            '"binding_grants_fact_authority": False',
            '"binding_grants_effect_authority": False',
            '"external_state_table": "NONE"',
            '"postcondition_achievement_claim": "NOT_YET_CLAIMED_PR2C"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/external_machine_runtime.py",
        (
            'EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID = "aasm.machine.external.runtime.v1"',
            '"state_observation_source": "EXISTING_PR1_DURABLE_OBSERVED_STATE_CLAIM"',
            '"effect_dispatch": "NONE"',
            '"executor_invocation": "NONE"',
            '"machine_state_mutation": "NONE"',
            "capability_report",
            "state_claim_report",
            "authorize_scoped_request",
            "add_evidence_guarded",
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/external_machine_runtime.py",
        (
            "EffectIntent",
            "EffectDispatchRequest",
            "EffectOwnership",
            "execute_effect",
            "claim_effect",
            "effect_executor",
        ),
    )
    require_tokens(
        ROOT / "src/aasm/runtime_v56_foundation.py",
        ("ExternalMachineRuntimeMixin", "StateAuthorityRuntimeMixin", "V55FoundationEngine"),
    )
    require_tokens(
        ROOT / "tests/test_external_machine.py",
        (
            "test_binding_references_do_not_create_fact_authority_or_effect_authority",
            "test_machine_observation_requires_durable_observed_state_claim_and_existing_binding",
            "test_machine_observation_rejects_subject_namespace_revision_and_capability_laundering",
            "test_valid_machine_observation_correlates_existing_claim_without_mutating_core_state_or_granting_authority",
            "test_sqlite_restart_reconstructs_bindings_and_observation_correlations_from_evidence",
        ),
    )

    public = validate_public_api_contract()
    require(public["valid"], f"active public contract invalid: {public['errors']}")
    contract = public_api_contract()
    require(contract["runtime_version"] == "0.56.1", "external machine is no longer composed into active runtime")
    require("external_machine" in contract, "external machine disappeared from active public contract")
    require(contract["external_machine"]["runtime"]["effect_dispatch"] == "NONE", "public PR-2A gained dispatch")
    require(contract["external_machine"]["runtime"]["executor_invocation"] == "NONE", "public PR-2A gained executor invocation")
    require(contract["external_machine"]["runtime"]["machine_state_mutation"] == "NONE", "public PR-2A mutates machine state")

    print("external machine binding, PR-1 observation correlation, schemas, and no-dispatch boundary: PASS")


if __name__ == "__main__":
    main()
