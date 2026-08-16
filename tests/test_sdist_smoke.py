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
    ".github/workflows/version-policy.yml",
    "compose.yaml",
    "docs/LANGGRAPH_ADAPTER.md",
    "docs/RELEASE_0.29.md",
    "docs/VERSIONING.md",
    "docs/runbooks/README.md",
    "examples/langgraph_adoption.py",
    "examples/research_synthesis_demo.py",
    "formal/AASMCalculus.tla",
    "profiles/research/profile.json",
    "schemas/langgraph-binding.schema.json",
    "schemas/langgraph-recovery.schema.json",
    "scripts/check_release_contracts.py",
    "scripts/check_version_policy.py",
    "scripts/release_artifacts.py",
    "scripts/release_artifacts_cli.py",
    "scripts/release_artifacts_core.py",
    "scripts/release_artifacts_github.py",
    "scripts/release_manifest.py",
    "src/aasm/__init__.py",
    "src/aasm/integrations/_langgraph_types.py",
    "src/aasm/integrations/_langgraph_binding.py",
    "src/aasm/integrations/_langgraph_conflict.py",
    "src/aasm/integrations/langgraph.py",
    "src/aasm/integrations/conformance.py",
    "src/aasm/integrations/conformance_registry.py",
    "src/aasm/integrations/langgraph_conformance.py",
    "src/aasm/runtime_v29.py",
    "src/aasm/runtime_v30.py",
    "tests/test_v28_operator_runbooks.py",
    "tests/test_v29_langgraph_adapter.py",
    "tests/test_v30_adapter_conformance.py",
    "src/aasm/scopes.py",
    "src/aasm/runtime_v31.py",
    "schemas/decision-scope.schema.json",
    "schemas/scope-dependency.schema.json",
    "schemas/scope-report.schema.json",
    "formal/AASMScopeHierarchy.tla",
    "docs/HIERARCHICAL_DECISION_SCOPES.md",
    "tests/test_v31_scopes.py",
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


def test_extracted_sdist_can_generate_a_fresh_manifest_without_release_inventory_freeze(tmp_path: Path) -> None:
    output = tmp_path / "SHA256SUMS.txt"
    subprocess.run(
        [sys.executable, "scripts/release_manifest.py", "--sha256", str(output)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "src/aasm/__init__.py" in text
    assert "docs/VERSIONING.md" in text
    assert "scripts/check_release_contracts.py" in text
