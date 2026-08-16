from __future__ import annotations

import json
from pathlib import Path

from aasm.event_causality import (
    CAUSAL_RELATIONS,
    CLOCK_QUALITIES,
    EVENT_CAUSALITY_CONTRACT_ID,
    PORTABLE_U63_MAX,
    event_causality_contract,
)
from aasm.event_causality_runtime import (
    EVENT_CAUSALITY_CAPABILITIES,
    EVENT_CAUSALITY_RUNTIME_CONTRACT_ID,
    event_causality_runtime_contract,
)
from aasm.observation_freshness import (
    FRESHNESS_AGE_BASES,
    FRESHNESS_REASONS,
    FRESHNESS_STATUSES,
    OBSERVATION_FRESHNESS_CONTRACT_ID,
    observation_freshness_contract,
)
from aasm.observation_freshness_runtime import (
    OBSERVATION_FRESHNESS_CAPABILITIES,
    OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID,
    observation_freshness_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing S3 causal/freshness contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: causal/freshness layer contains forbidden hidden-clock/authority/mutation tokens {present}")


def main() -> None:
    causal = event_causality_contract()
    causal_runtime = event_causality_runtime_contract()
    freshness = observation_freshness_contract()
    freshness_runtime = observation_freshness_runtime_contract()

    require(causal["contract_id"] == EVENT_CAUSALITY_CONTRACT_ID, "causal event contract drift")
    require(causal["clock_qualities"] == list(CLOCK_QUALITIES), "causal clock-quality enum drift")
    require(causal["relations"] == list(CAUSAL_RELATIONS), "causal relation enum drift")
    require(causal["portable_integer_range"] == f"0..{PORTABLE_U63_MAX}", "causal portable integer range drift")
    require(causal["local_event_identity"] == "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE", "causal local identity drift")
    require(causal["receipt_order_implies_source_order"] is False, "receipt order became source order")
    require(causal["host_wall_clock"] == "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED", "host wall clock became causal truth")
    require(causal["relation_grants_fact_authority"] is False, "causal relation grants fact authority")
    require(causal["relation_grants_effect_authority"] is False, "causal relation grants effect authority")
    require(causal["event_identity_grants_authority"] is False, "causal identity grants authority")
    require(causal["parallel_event_ledger"] == "NONE", "parallel causal event ledger introduced")
    require(causal["parallel_truth_table"] == "NONE", "parallel causal truth table introduced")

    require(causal_runtime["contract_id"] == EVENT_CAUSALITY_RUNTIME_CONTRACT_ID, "causal runtime contract drift")
    require(causal_runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "causal runtime bypassed Evidence/event replay")
    require(causal_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "causal runtime introduced parallel authority")
    require(causal_runtime["capabilities"] == EVENT_CAUSALITY_CAPABILITIES, "causal capability registry drift")
    require(causal_runtime["core_aasm_event_log"] == "UNCHANGED_AND_REMAINS_REPLAY_LEDGER", "causal runtime replaced AASM event log")
    require(causal_runtime["ingest_order"] == "MAY_DIFFER_FROM_SOURCE_SEQUENCE", "causal runtime equated ingest and source order")
    require(causal_runtime["same_node_boot_order"] == "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER", "local order semantics drift")
    require(causal_runtime["relation_consistency"] == "SAME_NODE_BOOT_RELATIONS_CANNOT_CONTRADICT_SEQUENCE_ORDER", "causal relation consistency drift")
    require(causal_runtime["fact_authority_creation"] == "NONE", "causal runtime creates fact authority")
    require(causal_runtime["effect_authority"] == "NONE", "causal runtime grants effect authority")
    require(causal_runtime["machine_state_mutation"] == "NONE", "causal runtime mutates machine state")
    require(causal_runtime["parallel_event_ledger"] == "NONE", "causal runtime added event ledger")

    require(freshness["contract_id"] == OBSERVATION_FRESHNESS_CONTRACT_ID, "freshness contract drift")
    require(freshness["statuses"] == list(FRESHNESS_STATUSES), "freshness status enum drift")
    require(freshness["age_bases"] == list(FRESHNESS_AGE_BASES), "freshness age-basis enum drift")
    require(freshness["reasons"] == list(FRESHNESS_REASONS), "freshness reason enum drift")
    require(freshness["reference_time"] == "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW", "freshness gained implicit host time")
    require(freshness["source_age"] == "REQUIRES_EXACT_REFERENCE_CLOCK_ID_AND_MINIMUM_CLOCK_QUALITY", "freshness source-age boundary drift")
    require(freshness["receipt_fallback"] == "OPTIONAL_AND_EXPLICITLY_MARKED_WEAKER_AGE_BASIS", "receipt fallback laundering drift")
    require(freshness["freshness_grants_fact_authority"] is False, "freshness grants fact authority")
    require(freshness["freshness_grants_effect_authority"] is False, "freshness grants effect authority")
    require(freshness["freshness_elevates_observation_authority"] is False, "freshness elevates observation authority")
    require(freshness["freshness_is_universal_admission"] is False, "freshness became universal admission")
    require(freshness["parallel_truth_table"] == "NONE", "freshness introduced truth table")

    require(freshness_runtime["contract_id"] == OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID, "freshness runtime contract drift")
    require(freshness_runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "freshness bypassed Evidence/event replay")
    require(freshness_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "freshness introduced parallel authority")
    require(freshness_runtime["capabilities"] == OBSERVATION_FRESHNESS_CAPABILITIES, "freshness capability registry drift")
    require(freshness_runtime["observation_source"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY", "freshness bypassed machine observation")
    require(freshness_runtime["claim_source"] == "EXISTING_DURABLE_OBSERVED_STATE_CLAIM_ONLY", "freshness bypassed observed claim")
    require(freshness_runtime["causal_source"] == "EXACT_DURABLE_CAUSAL_EVENT_ID_AND_FINGERPRINT", "freshness causal binding drift")
    require(freshness_runtime["reference_time_source"] == "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW", "runtime uses implicit host now")
    require(freshness_runtime["fact_authority_creation"] == "NONE", "freshness runtime creates fact authority")
    require(freshness_runtime["effect_authority"] == "NONE", "freshness runtime grants effect authority")
    require(freshness_runtime["observation_authority_elevation"] == "NONE", "freshness runtime elevates observation authority")
    require(freshness_runtime["universal_admission"] == "NONE", "freshness runtime grants universal admission")
    require(freshness_runtime["parallel_observation_store"] == "NONE", "freshness runtime introduced observation store")
    require(freshness_runtime["parallel_truth_table"] == "NONE", "freshness runtime introduced truth table")

    causal_schema = json.loads((ROOT / "schemas" / "causal-event.schema.json").read_text(encoding="utf-8"))
    relation_schema = json.loads((ROOT / "schemas" / "causal-relation.schema.json").read_text(encoding="utf-8"))
    freshness_schema = json.loads((ROOT / "schemas" / "observation-freshness.schema.json").read_text(encoding="utf-8"))
    require(causal_schema["properties"]["contract_id"]["const"] == EVENT_CAUSALITY_CONTRACT_ID, "causal-event schema drift")
    require(relation_schema["properties"]["contract_id"]["const"] == EVENT_CAUSALITY_CONTRACT_ID, "causal-relation schema drift")
    require(freshness_schema["properties"]["contract_id"]["const"] == OBSERVATION_FRESHNESS_CONTRACT_ID, "freshness schema drift")
    require(causal_schema["properties"]["sequence"]["maximum"] == PORTABLE_U63_MAX, "causal schema integer bound drift")

    require_tokens(
        ROOT / "src/aasm/event_causality.py",
        (
            'EVENT_CAUSALITY_CONTRACT_ID = "aasm.event.causality.v1"',
            "PORTABLE_U63_MAX = (1 << 63) - 1",
            "class CausalEventIdentity",
            "def local_identity_payload(",
            "class CausalRelation",
            '"receipt_order_implies_source_order": False',
            '"parallel_event_ledger": "NONE"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/event_causality_runtime.py",
        (
            'EVENT_CAUSALITY_RUNTIME_CONTRACT_ID = "aasm.event.causality.runtime.v1"',
            '"record": "event.causality.record"',
            '"relate": "event.causality.relate"',
            "self.machine_state_observation_report(",
            "self.state_claim_report(",
            "self.authorize_scoped_request(",
            "self.add_evidence_guarded(",
            "def _validate_relation_local_order(",
            '"host_context_time_grants_order": False',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/observation_freshness.py",
        (
            'OBSERVATION_FRESHNESS_CONTRACT_ID = "aasm.observation.freshness.v1"',
            "class ObservationFreshnessAssessment",
            "def assess_freshness(",
            '"freshness_is_universal_admission": False',
            '"assessment_id": "EXACT_INPUT_POLICY_AND_REFERENCE_CONTEXT"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/observation_freshness_runtime.py",
        (
            'OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID = "aasm.observation.freshness.runtime.v1"',
            '"assess": "observation.freshness.assess"',
            "self.machine_state_observation_report(",
            "self.causal_event_report(",
            "assess_freshness(",
            "self.authorize_scoped_request(",
            '"authority_context_time_is_freshness_reference": False',
            '"universal_admission": "NONE"',
        ),
    )

    for path in (
        ROOT / "src/aasm/event_causality.py",
        ROOT / "src/aasm/event_causality_runtime.py",
        ROOT / "src/aasm/observation_freshness.py",
        ROOT / "src/aasm/observation_freshness_runtime.py",
    ):
        forbid_tokens(
            path,
            (
                "time.time(",
                "time_ns(",
                "datetime.now(",
                "self.record_state_claim(",
                "self.register_fact_authority(",
                "self.propose_effect(",
                "self.authorize_effect(",
                "self.execute_effect(",
            ),
        )

    require_tokens(
        ROOT / "tests/test_causal_freshness.py",
        (
            "test_reboot_epoch_allows_sequence_reset_without_event_identity_collision",
            "test_receipt_order_does_not_override_same_node_boot_source_sequence",
            "test_same_node_boot_relations_cannot_contradict_known_local_sequence",
            "test_textpcb_style_recent_drc_observation_is_stale_when_project_revision_advanced",
            "test_receipt_fallback_is_explicitly_marked_and_can_be_fresh",
            "test_sqlite_restart_reconstructs_causal_event_relation_and_freshness_without_drift",
        ),
    )

    print("S3 causal identity and freshness preserve explicit boot/sequence/clock/revision semantics, no hidden host time, no authority elevation, and portable replay boundaries: PASS")


if __name__ == "__main__":
    main()
