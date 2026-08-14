import json

from aasm import __version__, validate_public_api_contract
from aasm.cli import build_parser
import aasm.cli_v45 as cli_v45


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


def test_modeling_conformance_cli_suppresses_backend_stdout_and_emits_one_json_document(monkeypatch, capsys):
    def noisy_backend(*, real=False):
        print("backend diagnostic that must not escape")
        return {"status": "PASS", "real_backends": bool(real), "checks": {"clean": True}, "results": {}}

    monkeypatch.setattr(cli_v45, "run_modeling_conformance", noisy_backend)
    cli_v45.main(["modeling-conformance", "--real"])
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "PASS"
    assert payload["real_backends"] is True
    assert "backend diagnostic" not in captured.out
