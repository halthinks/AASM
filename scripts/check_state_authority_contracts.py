from __future__ import annotations

import json
from pathlib import Path

from aasm import public_api_contract, validate_public_api_contract
from aasm.state_authority import (
    FACT_AUTHORITY_CONTRACT_ID,
    STATE_CLAIM_CONTRACT_ID,
    STATE_CLAIM_KINDS,
    state_authority_contract,
)
from aasm.state_authority_runtime import (
    STATE_AUTHORITY_CAPABILITIES,
    STATE_AUTHORITY_RUNTIME_CONTRACT_ID,
    state_authority_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing state-authority contract tokens {missing}")


def main() -> None:
    semantic = state_authority_contract()
    runtime = state_authority_runtime_contract()
    require(semantic["fact_authority_contract_id"] == FACT_AUTHORITY_CONTRACT_ID, "fact authority contract drift")
    require(semantic["state_claim_contract_id"] == STATE_CLAIM_CONTRACT_ID, "state claim contract drift")
    require(semantic["claim_kinds"] == list(STATE_CLAIM_KINDS), "state claim kinds drift")
    require(semantic["aggregation_grants_authority"] is False, "aggregation gained authority")
    require(semantic["fact_authority_grants_effect_authority"] is False, "fact authority gained effect authority")
    require(semantic["state_claim_grants_effect_authority"] is False, "state claim gained effect authority")
    require(semantic["machine_state_mutation"] == "NONE_BY_THIS_CONTRACT", "semantic contract mutates machine state")
    require(runtime["contract_id"] == STATE_AUTHORITY_RUNTIME_CONTRACT_ID, "state authority runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel state-authority persistence introduced")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel authority evaluator introduced")
    require(runtime["parallel_truth_table"] == "NONE", "parallel physical truth table introduced")
    require(runtime["machine_state_mutation"] == "NONE", "state claim runtime mutates machine state")
    require(runtime["effect_authority"] == "NONE", "state authority runtime gained actuator rights")
    require(runtime["aggregation_grants_authority"] is False, "runtime aggregation gained authority")
    require(runtime["capabilities"] == STATE_AUTHORITY_CAPABILITIES, "state authority capability registry drift")

    schemas = {
        "fact-authority.schema.json": FACT_AUTHORITY_CONTRACT_ID,
        "state-claim.schema.json": STATE_CLAIM_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    require_tokens(
        ROOT / "src/aasm/state_authority.py",
        (
            'FACT_AUTHORITY_CONTRACT_ID = "aasm.fact.authority.v1"',
            'STATE_CLAIM_CONTRACT_ID = "aasm.state.claim.v1"',
            '"DESIRED"', '"PREDICTED"', '"OBSERVED"', '"AUTHORITATIVE"',
            '"aggregation_grants_authority": False',
            '"fact_authority_grants_effect_authority": False',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/state_authority_runtime.py",
        (
            'STATE_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.state.authority.runtime.v1"',
            '"parallel_truth_table": "NONE"',
            '"machine_state_mutation": "NONE"',
            '"effect_authority": "NONE"',
            "authorize_scoped_request",
            "add_evidence_guarded",
            "register_fact_authority",
            "record_state_claim",
        ),
    )
    require_tokens(
        ROOT / "src/aasm/runtime_v56_foundation.py",
        ("StateAuthorityRuntimeMixin", "SolverProvenanceRuntimeMixin", "V55FoundationEngine"),
    )
    require_tokens(
        ROOT / "tests/test_state_authority.py",
        (
            "test_observation_does_not_become_authoritative_without_matching_fact_authority",
            "test_two_agreeing_observations_do_not_vote_themselves_into_authority",
            "test_desired_predicted_and_observed_claims_do_not_mutate_core_machine_or_calculus_state",
            "test_sqlite_restart_reconstructs_state_authority_only_from_existing_evidence_history",
        ),
    )

    public = validate_public_api_contract()
    require(public["valid"], f"active public contract invalid: {public['errors']}")
    contract = public_api_contract()
    require(contract["runtime_version"] == "0.56.1", "state authority is no longer composed into active runtime")
    require("state_authority" in contract, "state authority disappeared from active public contract")
    require(contract["state_authority"]["runtime"]["parallel_truth_table"] == "NONE", "public state-authority truth boundary drift")
    require(contract["state_authority"]["runtime"]["effect_authority"] == "NONE", "public state-authority effect boundary drift")

    print("state authority contracts, runtime composition, schemas, and adversarial surface: PASS")


if __name__ == "__main__":
    main()
