from __future__ import annotations

import pytest

from aasm.provider_status_v2 import (
    ProviderStatusMap,
    ProviderStatusRule,
    highs_status_map,
    map_provider_status,
    ortools_cp_sat_status_map,
    provider_status_map_contract,
    pysat_cadical_status_map,
)


def test_provider_status_contract_forbids_fuzzy_and_substring_mapping():
    contract = provider_status_map_contract()
    assert contract["mapping"] == "EXACT_NATIVE_ENUM_NAME_AND_OR_CODE_RULES_ONLY"
    assert contract["fuzzy_matching"] == "FORBIDDEN"
    assert contract["substring_inference"] == "FORBIDDEN"
    assert contract["ambiguous_mapping"] == "FAIL_CLOSED"
    assert contract["truth_authority"] == "NONE"


def test_ortools_native_enum_values_map_exactly():
    mapping = ortools_cp_sat_status_map("9.15.6755")
    optimal = map_provider_status(mapping, raw_status="OPTIMAL", raw_status_code="4", has_incumbent=True, objective_present=True)
    model_invalid = map_provider_status(mapping, raw_status="MODEL_INVALID", raw_status_code="1")
    unknown = map_provider_status(mapping, raw_status="UNKNOWN", raw_status_code="0")
    assert optimal.normalized_status == "OPTIMAL"
    assert optimal.incumbent_eligibility == "REQUIRED"
    assert model_invalid.normalized_status == "MODEL_INVALID"
    assert model_invalid.termination.reason == "MODEL_INVALID"
    assert unknown.normalized_status == "UNKNOWN_NO_SOLUTION"


def test_highs_enum_codes_cover_distinct_negative_limit_and_interrupt_states():
    mapping = highs_status_map("1.14.0")
    assert map_provider_status(mapping, raw_status="kInfeasible", raw_status_code="8", objective_present=True).normalized_status == "INFEASIBLE"
    assert map_provider_status(mapping, raw_status="kUnboundedOrInfeasible", raw_status_code="9", objective_present=True).normalized_status == "INFEASIBLE_OR_UNBOUNDED"
    assert map_provider_status(mapping, raw_status="kUnbounded", raw_status_code="10", objective_present=True).normalized_status == "UNBOUNDED"
    assert map_provider_status(mapping, raw_status="kTimeLimit", raw_status_code="13", has_incumbent=True, objective_present=True).normalized_status == "TIME_LIMIT_WITH_INCUMBENT"
    assert map_provider_status(mapping, raw_status="kIterationLimit", raw_status_code="14", objective_present=True).normalized_status == "ITERATION_LIMIT_NO_SOLUTION"
    assert map_provider_status(mapping, raw_status="kSolutionLimit", raw_status_code="16", has_incumbent=True, objective_present=True).normalized_status == "SOLUTION_LIMIT_WITH_INCUMBENT"
    assert map_provider_status(mapping, raw_status="kInterrupt", raw_status_code="17", objective_present=True).normalized_status == "USER_INTERRUPT_NO_SOLUTION"


def test_generic_exact_rules_cover_memory_provider_and_unsupported_classes_without_guessing():
    mapping = ProviderStatusMap(
        "qualified-fixture",
        "1.0",
        "aasm.fixture",
        "1.0",
        (
            ProviderStatusRule("MEMORY_LIMIT", "MEMORY_LIMIT_DYNAMIC", raw_status="MEMORY", raw_status_code="21", incumbent_eligibility="VALIDATED_IF_PRESENT", limit_unit="bytes", provider_version_range="==1.0"),
            ProviderStatusRule("PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE", raw_status="UNAVAILABLE", raw_status_code="22", provider_version_range="==1.0"),
            ProviderStatusRule("UNSUPPORTED_FEATURE", "UNSUPPORTED_FEATURE", raw_status="UNSUPPORTED", raw_status_code="23", provider_version_range="==1.0"),
        ),
    )
    memory = map_provider_status(mapping, raw_status="MEMORY", raw_status_code="21", has_incumbent=True, objective_present=True)
    unavailable = map_provider_status(mapping, raw_status="UNAVAILABLE", raw_status_code="22")
    unsupported = map_provider_status(mapping, raw_status="UNSUPPORTED", raw_status_code="23")
    assert memory.normalized_status == "MEMORY_LIMIT_WITH_INCUMBENT"
    assert memory.termination.reason == "MEMORY_LIMIT"
    assert memory.termination.limit_unit == "bytes"
    assert unavailable.normalized_status == "PROVIDER_UNAVAILABLE"
    assert unavailable.termination.reason == "PROVIDER_UNAVAILABLE"
    assert unsupported.normalized_status == "UNSUPPORTED_FEATURE"
    assert unsupported.termination.reason == "UNSUPPORTED_FEATURE"


def test_highs_model_error_is_model_invalid_not_infeasible():
    mapped = map_provider_status(highs_status_map("1.14.0"), raw_status="kModelError", raw_status_code="2", objective_present=True)
    assert mapped.normalized_status == "MODEL_INVALID"
    assert mapped.termination.reason == "MODEL_INVALID"


def test_unknown_raw_status_is_preserved_and_never_guessed_from_fragments():
    mapping = highs_status_map("1.14.0")
    mapped = map_provider_status(
        mapping,
        raw_status="kAlmostTimeLimitButNotActuallyAStatus",
        raw_status_code="999",
        raw_message="future provider status",
        objective_present=True,
    )
    assert mapped.normalized_status == "UNKNOWN_NO_SOLUTION"
    assert mapped.termination.reason == "UNKNOWN"
    assert mapped.termination.raw_status_code == "999"
    assert mapped.mapping_status == "NO_EXACT_RULE"


def test_incumbent_eligibility_fails_closed():
    mapping = highs_status_map("1.14.0")
    with pytest.raises(ValueError, match="forbids an incumbent"):
        map_provider_status(mapping, raw_status="kInfeasible", raw_status_code="8", has_incumbent=True, objective_present=True)
    with pytest.raises(ValueError, match="requires an incumbent"):
        map_provider_status(mapping, raw_status="kOptimal", raw_status_code="7", has_incumbent=False, objective_present=True)


def test_pysat_map_claims_only_current_boolean_solve_path():
    mapping = pysat_cadical_status_map("1.9.dev14")
    assert map_provider_status(mapping, raw_status="SAT", raw_status_code="1", has_incumbent=True).normalized_status == "SAT"
    assert map_provider_status(mapping, raw_status="UNSAT", raw_status_code="0").normalized_status == "UNSAT"
    assert mapping.metadata["limit_specific_statuses"] == "UNSUPPORTED_BY_CURRENT_AASM_CADICAL_ADAPTER"


def test_duplicate_exact_rule_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        ProviderStatusMap(
            "provider", "1", "adapter", "1",
            (
                ProviderStatusRule("TIME_LIMIT", "TIME_LIMIT_DYNAMIC", raw_status="LIMIT"),
                ProviderStatusRule("NODE_LIMIT", "NODE_LIMIT_DYNAMIC", raw_status="LIMIT"),
            ),
        )


def test_rule_declares_normalized_status_eligibility_and_version_range():
    rule = highs_status_map("1.14.0").rules[0]
    assert rule.normalized_status
    assert rule.incumbent_eligibility in {"NEVER", "VALIDATED_IF_PRESENT", "REQUIRED"}
    assert rule.bound_eligibility in {"NEVER", "IF_PROVIDER_SUPPLIED", "EXPECTED_IF_OBJECTIVE"}
    assert rule.certificate_eligibility in {"NONE", "OPTIONAL", "PROVIDER_SPECIFIC"}
    assert rule.provider_version_range == "==1.14.0"
