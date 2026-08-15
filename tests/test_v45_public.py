import io
import json
from contextlib import redirect_stdout

from aasm import __version__, validate_public_api_contract
from aasm.cli import build_parser, main


def test_v45_public_contract_and_cli_are_active():
    assert __version__ == "0.53.0"
    report = validate_public_api_contract()
    assert report["valid"], report
    assert report["contract"]["contract_version"] == "0.29.0"
    assert report["contract"]["convex_optimization"]["contract_id"] == "aasm.optimization.convex.v1"
    assert report["contract"]["convex_optimization"]["result_authority"] == "EVIDENCE_ONLY"
    assert report["contract"]["pulp_adapter"]["authority"] == "TRANSLATION_ONLY"
    assert report["contract"]["pulp_adapter"]["solver_execution"] == "NEVER"
    help_text = build_parser().format_help()
    for name in ("convex-optimization-contract", "pulp-adapter-contract", "modeling-conformance"):
        assert name in help_text


def test_modeling_conformance_cli_emits_one_clean_json_document(monkeypatch):
    import aasm.cli_v45 as cli_v45

    def noisy_conformance(*, real=False):
        print("backend diagnostic that must not escape")
        return {"status": "PASS", "real_backends": bool(real), "checks": {"clean": True}}

    monkeypatch.setattr(cli_v45, "run_modeling_conformance", noisy_conformance)
    stream = io.StringIO()
    with redirect_stdout(stream):
        main(["modeling-conformance", "--real"])
    parsed = json.loads(stream.getvalue())
    assert parsed["status"] == "PASS"
    assert parsed["real_backends"] is True
