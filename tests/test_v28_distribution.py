from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from aasm import __version__, public_api_contract


ROOT = Path(__file__).resolve().parents[1]


def _release_module():
    path = ROOT / "scripts" / "release_artifacts.py"
    spec = importlib.util.spec_from_file_location("aasm_release_artifacts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_distribution_metadata_and_adoption_contract_are_aligned():
    assert __version__ == "0.28.0"
    contract = public_api_contract()
    assert contract["runtime_version"] == __version__
    assert contract["distribution"]["package"] == "aasm-runtime"
    assert contract["distribution"]["release_workflow"] == (
        ".github/workflows/release.yml"
    )
    assert contract["distribution"]["checksums"] == "SHA256SUMS.txt"
    assert set(contract["operator_runbooks"]) == {
        "lease-loss",
        "requirement-change",
        "learned-no-good",
        "human-approval",
        "replay-fork",
        "unknown-effect",
        "history-diagnosis",
    }


def test_release_history_is_valid_and_names_maintained_tags():
    module = _release_module()
    report = module.verify_release_history(ROOT / "release-history.json")
    assert report["valid"] is True, report
    assert [row["tag"] for row in report["releases"]] == [
        "v0.25.1",
        "v0.25.2",
        "v0.26.0",
        "v0.27.0",
    ]


def test_release_artifact_tool_verifies_wheel_members_and_metadata(tmp_path):
    module = _release_module()
    wheel = tmp_path / "aasm_runtime-0.28.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "aasm_runtime-0.28.0.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: aasm-runtime\nVersion: 0.28.0\n",
        )
        for name in module.REQUIRED_WHEEL_MEMBERS:
            archive.writestr(name, "{}\n" if name.endswith(".json") else "# fixture\n")
    report = module.verify_wheel(wheel, expected_version="0.28.0")
    assert report["valid"] is True, report
    assert len(report["sha256"]) == 64


def test_release_artifact_manifest_is_deterministic_and_checksummed(tmp_path):
    module = _release_module()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "aasm_runtime-0.28.0-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "aasm_runtime-0.28.0.tar.gz").write_bytes(b"sdist")
    checksums = tmp_path / "SHA256SUMS.txt"
    manifest_path = tmp_path / "release-manifest.json"
    manifest = module.write_release_manifests(
        dist,
        checksums_path=checksums,
        json_path=manifest_path,
        commit_sha="a" * 40,
    )
    assert manifest["package"] == "aasm-runtime"
    assert manifest["version"] == "0.28.0"
    assert [row["name"] for row in manifest["files"]] == [
        "aasm_runtime-0.28.0-py3-none-any.whl",
        "aasm_runtime-0.28.0.tar.gz",
    ]
    text = checksums.read_text(encoding="utf-8")
    assert "aasm_runtime-0.28.0-py3-none-any.whl" in text
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest


def test_release_workflow_builds_verifies_releases_and_gates_pypi():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    for token in [
        "workflow_run:",
        'workflows: ["CI"]',
        "python -m build",
        "python -m twine check",
        "verify-wheel",
        "verify-sdist",
        "SHA256SUMS.txt",
        "gh release create",
        '--target "$COMMIT_SHA"',
        "tag_commit()",
        "pypa/gh-action-pypi-publish@release/v1",
        "AASM_PUBLISH_PYPI",
    ]:
        assert token in workflow
    assert "git tag -a" not in workflow
    assert 'git push origin "refs/tags/' not in workflow


def test_release_docs_make_external_pypi_gate_explicit():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs" / "COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    release_process = (ROOT / "docs" / "RELEASE_PROCESS.md").read_text(
        encoding="utf-8"
    )
    assert "v0.28.0" in readme
    assert "v0.29.0 — Thin LangGraph Adapter" in readme
    assert "aasm.remote.v1 / 0.19.0" in readme
    assert "pre-1.0" in compatibility
    assert "immutable release tag" in compatibility
    assert "PyPI Trusted Publisher" in release_process
    assert "AASM_PUBLISH_PYPI" in release_process
    assert "GitHub Release API" in release_process


def test_release_artifact_cli_reports_project_version():
    completed = subprocess.run(
        [sys.executable, "scripts/release_artifacts.py", "version"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stdout.strip() == "0.28.0"
