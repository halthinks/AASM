from aasm import __version__, advanced_optimization_contract, validate_public_api_contract
from aasm.cli import build_parser


def test_v46_public_contract_and_cli_are_active():
    assert __version__ == "0.54.0"
    report = validate_public_api_contract()
    assert report["valid"], report
    assert report["contract"]["contract_version"] == "0.30.0"
    advanced = report["contract"]["advanced_optimization"]
    assert advanced["contract_id"] == "aasm.optimization.advanced.v1"
    assert advanced["result_authority"] == "EVIDENCE_ONLY"
    assert advanced["truth_rule"] == "SEARCH_STATE_NEVER_PROMOTES_TRUTH"
    assert advanced["incremental_sat"]["learned_state"] == "EPHEMERAL_PERFORMANCE_ONLY"
    help_text = build_parser().format_help()
    for name in (
        "advanced-optimization-contract",
        "advanced-optimization-blueprint",
        "advanced-optimization-conformance",
    ):
        assert name in help_text


def test_advanced_contract_preserves_single_scheduler_and_non_authoritative_search_state():
    contract = advanced_optimization_contract()
    assert contract["scheduler"] == "EXISTING_AASM_RESOURCE_WORKER_LEASE"
    assert contract["result_authority"] == "EVIDENCE_ONLY"
    assert contract["truth_rule"] == "SEARCH_STATE_NEVER_PROMOTES_TRUTH"
    assert contract["incremental_sat"]["learned_state"] == "EPHEMERAL_PERFORMANCE_ONLY"
