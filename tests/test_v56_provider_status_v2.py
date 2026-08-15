from __future__ import annotations

import pytest

from aasm.provider_status_v2 import (
    ProviderStatusMap,
    ProviderStatusRule,
    map_provider_termination,
    provider_status_map_contract,
)


def _map() -> ProviderStatusMap:
    return ProviderStatusMap(
        "highs",
        "1.9.0",
        "aasm.highs",
        "0.2.0",
        (
            ProviderStatusRule("COMPLETED", raw_status="kHighsModelStatusOptimal"),
            ProviderStatusRule("TIME_LIMIT", raw_status="kHighsModelStatusTimeLimit", limit_unit="seconds"),
            ProviderStatusRule("NODE_LIMIT", raw_status_code="17", limit_unit="nodes"),
            ProviderStatusRule("NUMERICAL_FAILURE", raw_status="kHighsModelStatusSolveError"),
        ),
    )


def test_provider_status_contract_forbids_fuzzy_mapping():
    contract = provider_status_map_contract()
    assert contract["mapping"] == "EXACT_RAW_STATUS_AND_OR_CODE_RULES_ONLY"
    assert contract["fuzzy_matching"] == "FORBIDDEN"
    assert contract["unknown_raw_status"] == "PRESERVE_RAW_PAYLOAD_AND_NORMALIZE_TERMINATION_UNKNOWN"
    assert contract["ambiguous_mapping"] == "FAIL_CLOSED"
    assert contract["truth_authority"] == "NONE"


def test_exact_raw_status_maps_and_preserves_payload():
    mapping = _map()
    termination = map_provider_termination(
        mapping,
        raw_status="kHighsModelStatusTimeLimit",
        raw_status_code="",
        raw_message="time limit reached after presolve",
        limit_value=60,
        metadata={"run": "abc"},
    )
    assert termination.reason == "TIME_LIMIT"
    assert termination.raw_status == "kHighsModelStatusTimeLimit"
    assert termination.raw_message == "time limit reached after presolve"
    assert termination.limit_value == 60.0
    assert termination.limit_unit == "seconds"
    assert termination.metadata["mapping_status"] == "EXACT_RULE"
    assert termination.metadata["provider_status_map_fingerprint"] == mapping.fingerprint


def test_exact_raw_code_can_map_when_status_text_changes():
    termination = map_provider_termination(
        _map(),
        raw_status="some-new-text",
        raw_status_code="17",
        limit_value=1000,
    )
    assert termination.reason == "NODE_LIMIT"
    assert termination.raw_status == "some-new-text"
    assert termination.raw_status_code == "17"
    assert termination.limit_unit == "nodes"


def test_unknown_raw_status_is_not_guessed():
    mapping = _map()
    termination = map_provider_termination(
        mapping,
        raw_status="kHighsModelStatusAlmostTimeLimit",
        raw_status_code="999",
        raw_message="unknown future status",
    )
    assert termination.reason == "UNKNOWN"
    assert termination.raw_status == "kHighsModelStatusAlmostTimeLimit"
    assert termination.raw_status_code == "999"
    assert termination.raw_message == "unknown future status"
    assert termination.metadata["mapping_status"] == "NO_EXACT_RULE"


def test_status_rule_requires_real_match_identity():
    with pytest.raises(ValueError, match="requires raw_status"):
        ProviderStatusRule("TIME_LIMIT")


def test_duplicate_exact_rule_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        ProviderStatusMap(
            "provider",
            "1",
            "adapter",
            "1",
            (
                ProviderStatusRule("TIME_LIMIT", raw_status="LIMIT"),
                ProviderStatusRule("NODE_LIMIT", raw_status="LIMIT"),
            ),
        )


def test_overlapping_partial_rules_fail_closed_when_both_match():
    mapping = ProviderStatusMap(
        "provider",
        "1",
        "adapter",
        "1",
        (
            ProviderStatusRule("TIME_LIMIT", raw_status="LIMIT"),
            ProviderStatusRule("NODE_LIMIT", raw_status_code="17"),
        ),
    )
    with pytest.raises(ValueError, match="ambiguous"):
        map_provider_termination(mapping, raw_status="LIMIT", raw_status_code="17")
