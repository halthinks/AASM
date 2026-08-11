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
    assert __version__ == "0.28.1"
    contract = public_api_contract()
    assert contract["runtime_version"] == __version__
    assert contract["distribution"]["package"] == "aasm-runtime"
    assert contract["distribution"]["release_workflow"] == (
        ".github/workflows/release.yml"
    )
    assert contract["distribution"]["checksums"] == "SHA256SUMS.txt"
    assert contract["distribution"]["reproducible_builds"] is True
    assert contract["distribution"]["historical_release_policy"] == "REPORT_ONLY"
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
    wheel = tmp_path / "aasm_runtime-0.28.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "aasm_runtime-0.28.1.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: aasm-runtime\nVersion: 0.28.1\n",
        )
        for name in module.REQUIRED_WHEEL_MEMBERS:
            archive.writestr(name, "{}\n" if name.endswith(".json") else "# fixture\n")
    report = module.verify_wheel(wheel, expected_version="0.28.1")
    assert report["valid"] is True, report
    assert len(report["sha256"]) == 64


def test_release_artifact_manifest_is_deterministic_and_checksummed(tmp_path):
    module = _release_module()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "aasm_runtime-0.28.1-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "aasm_runtime-0.28.1.tar.gz").write_bytes(b"sdist")
    (dist / "historical-release-report.json").write_text(
        '{"valid": true}\n', encoding="utf-8"
    )
    checksums = dist / "SHA256SUMS.txt"
    manifest_path = dist / "release-manifest.json"
    manifest = module.write_release_manifests(
        dist,
        checksums_path=checksums,
        json_path=manifest_path,
        commit_sha="a" * 40,
    )
    assert manifest["schema_version"] == 2
    assert manifest["package"] == "aasm-runtime"
    assert manifest["version"] == "0.28.1"
    assert [row["name"] for row in manifest["files"]] == [
        "aasm_runtime-0.28.1-py3-none-any.whl",
        "aasm_runtime-0.28.1.tar.gz",
        "historical-release-report.json",
    ]
    text = checksums.read_text(encoding="utf-8")
    assert "aasm_runtime-0.28.1-py3-none-any.whl" in text
    assert "historical-release-report.json" in text
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest


def test_two_build_comparison_rejects_byte_drift(tmp_path):
    module = _release_module()
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    for directory in (left, right):
        (directory / "aasm_runtime-0.28.1-py3-none-any.whl").write_bytes(b"wheel")
        (directory / "aasm_runtime-0.28.1.tar.gz").write_bytes(b"sdist")
    assert module.compare_builds(left, right)["valid"] is True
    (right / "aasm_runtime-0.28.1.tar.gz").write_bytes(b"changed")
    report = module.compare_builds(left, right)
    assert report["valid"] is False
    assert "non-reproducible artifact" in " ".join(report["errors"])


def test_historical_release_report_treats_missing_tags_as_non_blocking():
    module = _release_module()
    history = {
        "releases": [
            {"tag": "v0.25.1", "commit": "a" * 40, "title": "old"},
            {"tag": "v0.25.2", "commit": "b" * 40, "title": "older"},
        ]
    }
    resolved = {"v0.25.1": None, "v0.25.2": "b" * 40}
    report = module.build_historical_release_report(
        history,
        resolve_tag=resolved.get,
        release_commit="c" * 40,
    )
    assert report["valid"] is True
    assert [row["status"] for row in report["records"]] == [
        "PENDING_OWNER_PUBLICATION",
        "VERIFIED",
    ]


def test_historical_release_report_fails_only_on_a_real_mismatch():
    module = _release_module()
    history = {
        "releases": [
            {"tag": "v0.25.1", "commit": "a" * 40, "title": "old"},
        ]
    }
    report = module.build_historical_release_report(
        history,
        resolve_tag=lambda _tag: "b" * 40,
    )
    assert report["valid"] is False
    assert report["records"][0]["status"] == "MISMATCH"


def test_remote_release_snapshot_requires_exact_names_sizes_and_hashes(tmp_path):
    module = _release_module()
    dist = tmp_path / "dist"
    dist.mkdir()
    names = [
        "aasm_runtime-0.28.1-py3-none-any.whl",
        "aasm_runtime-0.28.1.tar.gz",
        "historical-release-report.json",
        "SHA256SUMS.txt",
        "release-manifest.json",
    ]
    for index, name in enumerate(names):
        (dist / name).write_bytes(f"asset-{index}".encode())
    release = {
        "tag_name": "v0.28.1",
        "draft": False,
        "assets": [
            {
                "name": name,
                "size": (dist / name).stat().st_size,
                "digest": f"sha256:{module.sha256_file(dist / name)}",
            }
            for name in names
        ],
    }
    report = module.verify_release_asset_snapshot(
        dist,
        release=release,
        resolved_tag_commit="a" * 40,
        expected_tag="v0.28.1",
        expected_commit="a" * 40,
    )
    assert report["valid"] is True, report
    release["assets"][0]["digest"] = "sha256:" + "0" * 64
    assert module.verify_release_asset_snapshot(
        dist,
        release=release,
        resolved_tag_commit="a" * 40,
        expected_tag="v0.28.1",
        expected_commit="a" * 40,
    )["valid"] is False


def test_release_workflow_builds_verifies_releases_and_gates_pypi():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    for token in [
        "workflow_run:",
        'workflows: ["CI"]',
        "should_release",
        'build==1.5.0',
        'twine==6.2.0',
        "compare-builds",
        "historical-report",
        "verify-github-release",
        "SOURCE_DATE_EPOCH",
        "SHA256SUMS.txt",
        "gh release create",
        '--target "$COMMIT_SHA"',
        "pypa/gh-action-pypi-publish@release/v1",
        "AASM_PUBLISH_PYPI",
    ]:
        assert token in workflow
    for forbidden in [
        "--clobber",
        "git tag -a",
        'git push origin "refs/tags/',
        "Backfill maintained historical source releases",
    ]:
        assert forbidden not in workflow


def test_release_docs_make_external_pypi_gate_explicit():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs" / "COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    release_process = (ROOT / "docs" / "RELEASE_PROCESS.md").read_text(
        encoding="utf-8"
    )
    assert "v0.28.1" in readme
    assert "v0.29.0 — Thin LangGraph Adapter" in readme
    assert "aasm.remote.v1 / 0.19.0" in readme
    assert "pre-1.0" in compatibility
    assert "immutable release tag" in compatibility
    assert "PyPI Trusted Publisher" in release_process
    assert "AASM_PUBLISH_PYPI" in release_process
    assert "GitHub Release API" in release_process
    assert "PENDING_OWNER_PUBLICATION" in release_process


def test_release_artifact_cli_reports_project_version():
    completed = subprocess.run(
        [sys.executable, "scripts/release_artifacts.py", "version"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stdout.strip() == "0.28.1"
