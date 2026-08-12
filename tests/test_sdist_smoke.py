from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from aasm import __version__, execute_operator_runbook, validate_public_api_contract

ROOT = Path(__file__).resolve().parents[1]
REPRESENTATIVE_MEMBERS = [
    ".dockerignore",
    ".gitignore",
    ".github/workflows/ci.yml",
    "compose.yaml",
    "docs/LANGGRAPH_ADAPTER.md",
    "docs/RELEASE_0.29.md",
    "docs/runbooks/README.md",
    "examples/langgraph_adoption.py",
    "examples/research_synthesis_demo.py",
    "formal/AASMCalculus.tla",
    "profiles/research/profile.json",
    "schemas/langgraph-binding.schema.json",
    "schemas/langgraph-recovery.schema.json",
    "scripts/check_release_contracts.py",
    "src/aasm/__init__.py",
    "src/aasm/integrations/_langgraph_types.py",
    "src/aasm/integrations/_langgraph_binding.py",
    "src/aasm/integrations/_langgraph_conflict.py",
    "src/aasm/integrations/langgraph.py",
    "src/aasm/runtime_v29.py",
    "tests/test_v28_operator_runbooks.py",
    "tests/test_v29_langgraph_adapter.py",
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


def test_extracted_sdist_file_inventory_is_self_consistent() -> None:
    subprocess.run(
        [sys.executable, "scripts/release_manifest.py", "--check-file-list"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
