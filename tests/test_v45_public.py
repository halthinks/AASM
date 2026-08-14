from aasm import __version__, validate_public_api_contract
from aasm.cli import build_parser


def test_v45_public_contract_and_cli_are_active():
    assert __version__ == "0.45.0"
    report = validate_public_api_contract()
    assert report["valid"], report
    assert report["contract"]["contract_version"] == "0.21.0"
    assert report["contract"]["convex_optimization"]["contract_id"] == "aasm.optimization.convex.v1"
    assert report["contract"]["convex_optimization"]["result_authority"] == "EVIDENCE_ONLY"
    assert report["contract"]["pulp_adapter"]["authority"] == "TRANSLATION_ONLY"
    assert report["contract"]["pulp_adapter"]["solver_execution"] == "NEVER"
    help_text = build_parser().format_help()
    for name in ("convex-optimization-contract", "pulp-adapter-contract", "modeling-conformance"):
        assert name in help_text
