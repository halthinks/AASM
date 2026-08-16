from __future__ import annotations

import json
from pathlib import Path

from aasm.state_conflict import (
    STATE_CONFLICT_ACTUAL_KINDS,
    STATE_CONFLICT_CONTRACT_ID,
    STATE_CONFLICT_EXPECTATION_KINDS,
    STATE_CONFLICT_REASONS,
    state_conflict_contract,
)
from aasm.state_conflict_runtime import (
    STATE_CONFLICT_CAPABILITIES,
    STATE_CONFLICT_RUNTIME_CONTRACT_ID,
    state_conflict_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing S3 state-conflict contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: state-conflict layer contains forbidden parallel-authority/truth/mutation tokens {present}")


def main() -> None:
    semantic = state_conflict_contract()
    runtime = state_conflict_runtime_contract()

    require(semantic["contract_id"] == STATE_CONFLICT_CONTRACT_ID, "state conflict contract drift")
    require(semantic["expectation_claim_kinds"] == list(STATE_CONFLICT_EXPECTATION_KINDS), "expectation kind drift")
    require(semantic["actual_claim_kinds"] == list(STATE_CONFLICT_ACTUAL_KINDS), "actual kind drift")
    require(semantic["conflict_reasons"] == list(STATE_CONFLICT_REASONS), "state conflict reason drift")
    require(semantic["comparison"] == "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY", "portable comparison drift")
    require(semantic["quantity_tolerance"] == "RESERVED_FOR_S4_QUANTITY_SEMANTICS", "S3 overclaims tolerance semantics")
    require(semantic["revision_mismatch"] == "DURABLE_CONFLICT_REASON_NOT_SILENT_NONCOMPARABILITY", "revision conflict drift")
    require(semantic["conflict_grants_fact_authority"] is False, "state conflict mints fact authority")
    require(semantic["conflict_grants_effect_authority"] is False, "state conflict mints effect authority")
    require(semantic["conflict_mutates_machine_state"] is False, "state conflict mutates machine state")
    require(semantic["conflict_mutates_state_claims"] is False, "state conflict rewrites claims")
    require(semantic["host_wall_clock_in_identity"] is False, "host time entered portable identity")
    require(semantic["python_object_identity_in_identity"] is False, "Python object identity entered portable identity")
    require(semantic["parallel_truth_table"] == "NONE", "parallel state-conflict truth table introduced")

    require(runtime["contract_id"] == STATE_CONFLICT_RUNTIME_CONTRACT_ID, "state conflict runtime contract drift")
    require(runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "parallel state-conflict persistence introduced")
    require(runtime["claim_source"] == "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY", "state conflict bypassed durable state claims")
    require(runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "parallel state-conflict authority introduced")
    require(runtime["capabilities"] == STATE_CONFLICT_CAPABILITIES, "state conflict capability registry drift")
    require(runtime["claim_mutation"] == "NONE", "state conflict runtime rewrites claims")
    require(runtime["machine_state_mutation"] == "NONE", "state conflict runtime mutates core machine state")
    require(runtime["fact_authority_creation"] == "NONE", "state conflict runtime creates fact authority")
    require(runtime["effect_authority"] == "NONE", "state conflict runtime grants effect authority")
    require(runtime["observation_authority_elevation"] == "NONE", "state conflict elevates observations")
    require(runtime["parallel_truth_table"] == "NONE", "state conflict runtime introduced parallel truth")
    require(runtime["parallel_dependency_graph"] == "NONE", "state conflict runtime introduced parallel dependency graph")

    schema = json.loads((ROOT / "schemas" / "state-conflict.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == STATE_CONFLICT_CONTRACT_ID, "state conflict schema contract drift")
    require(schema["properties"]["reasons"]["items"]["enum"] == list(STATE_CONFLICT_REASONS), "state conflict schema reason drift")

    require_tokens(
        ROOT / "src/aasm/state_conflict.py",
        (
            'STATE_CONFLICT_CONTRACT_ID = "aasm.state.conflict.v1"',
            "def state_conflict_reasons(",
            "class StateConflict",
            "canonical_semantic_json",
            "semantic_fingerprint",
            '"host_wall_clock_in_identity": False',
            '"python_object_identity_in_identity": False',
            '"resolution_lifecycle": "NOT_DEFINED_IN_V1_CONFLICT_EVIDENCE_IS_IMMUTABLE"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/state_conflict_runtime.py",
        (
            'STATE_CONFLICT_RUNTIME_CONTRACT_ID = "aasm.state.conflict.runtime.v1"',
            '"record": "state.conflict.record"',
            "self.state_claim_report(",
            "self.authorize_scoped_request(",
            "self.add_evidence_guarded(",
            "StateConflict.from_claims",
            '"semantic_identity_includes_recorder": False',
            '"semantic_identity_includes_host_time": False',
        ),
    )
    forbid_tokens(
        ROOT / "src/aasm/state_conflict_runtime.py",
        (
            "self.record_state_claim(",
            "self.register_fact_authority(",
            "self.propose_effect(",
            "self.authorize_effect(",
            "self.execute_effect(",
            "EffectOwnership",
            "EffectDispatchRequest",
        ),
    )
    require_tokens(
        ROOT / "tests/test_state_conflict.py",
        (
            "test_portable_value_comparison_uses_canonical_json_not_python_equality_or_mapping_order",
            "test_durable_conflict_preserves_claims_authorities_effects_and_core_machine_state",
            "test_observed_only_actual_can_be_recorded_without_authority_elevation",
            "test_textpcb_style_out_of_band_project_revision_is_a_generic_revision_conflict",
            "test_sqlite_restart_reconstructs_conflict_from_existing_evidence_without_identity_drift",
        ),
    )

    print("S3 state conflict preserves both state histories, revision conflicts, scoped Evidence recording, portable identity, and no-authority-elevation boundaries: PASS")


if __name__ == "__main__":
    main()
