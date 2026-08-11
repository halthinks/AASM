from __future__ import annotations

from pathlib import Path

from aasm import __version__, execute_operator_runbook, validate_public_api_contract

ROOT = Path(__file__).resolve().parents[1]
REPRESENTATIVE_MEMBERS = [
    ".github/workflows/ci.yml",
    "compose.yaml",
    "docs/runbooks/README.md",
    "examples/research_synthesis_demo.py",
    "formal/AASMCalculus.tla",
    "profiles/research/profile.json",
    "schemas/machine-definition.schema.json",
    "scripts/check_release_contracts.py",
    "src/aasm/__init__.py",
    "tests/test_v28_operator_runbooks.py",
]


def test_extracted_sdist_contains_repository_contracts() -> None:
    missing = [path for path in REPRESENTATIVE_MEMBERS if not (ROOT / path).is_file()]
    assert not missing, missing


def test_extracted_sdist_executes_public_contract_and_runbook() -> None:
    report = validate_public_api_contract()
    assert report["valid"] is True, report
    assert report["contract"]["runtime_version"] == __version__
    result = execute_operator_runbook("history-diagnosis")
    assert result.valid is True, result.to_dict()
