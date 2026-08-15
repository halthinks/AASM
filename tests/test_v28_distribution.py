from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import zipfile
from aasm import __version__, public_api_contract

ROOT=Path(__file__).resolve().parents[1]; VERSION=__version__

def _release_module():
    path=ROOT/"scripts"/"release_artifacts.py"; spec=importlib.util.spec_from_file_location("aasm_release_artifacts",path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module

def test_distribution_metadata_and_adoption_contract_are_aligned():
    contract=public_api_contract(); assert contract["runtime_version"]==VERSION; assert contract["distribution"]["package"]=="aasm-runtime"; assert contract["distribution"]["reproducible_builds"] is True

def test_release_history_contract_is_valid(): assert _release_module().verify_release_history(ROOT/"release-history.json")["valid"] is True

def test_release_artifact_tool_verifies_current_wheel_metadata(tmp_path):
    module=_release_module(); wheel=tmp_path/f"aasm_runtime-{VERSION}-py3-none-any.whl"
    with zipfile.ZipFile(wheel,"w") as archive:
        archive.writestr(f"aasm_runtime-{VERSION}.dist-info/METADATA",f"Metadata-Version: 2.4\nName: aasm-runtime\nVersion: {VERSION}\n")
        for name in module.REQUIRED_WHEEL_MEMBERS: archive.writestr(name,"{}\n" if name.endswith(".json") else "# fixture\n")
    assert module.verify_wheel(wheel,expected_version=VERSION)["valid"] is True

def test_release_workflow_is_immutable_and_version_agnostic():
    workflow=(ROOT/".github"/"workflows"/"release.yml").read_text(encoding="utf-8")
    for token in ['workflows: ["CI"]',"aasm/ci-summary","aasm/formal-assurance","compare-builds","SOURCE_DATE_EPOCH","SHA256SUMS.txt",'gh release create "$TAG"','--target "$COMMIT_SHA"','--notes-file docs/CURRENT_RELEASE.md',"verify-github-release"]: assert token in workflow
    assert "--clobber" not in workflow

def test_release_docs_show_current_version_next_milestone_and_remote_protocol():
    readme=(ROOT/"README.md").read_text(encoding="utf-8"); current=(ROOT/"docs"/"CURRENT_RELEASE.md").read_text(encoding="utf-8"); assert f"v{VERSION}" in readme; assert "Next release" in readme; assert "aasm.remote.v1 / 0.19.0" in current

def test_release_artifact_cli_reports_project_version():
    completed=subprocess.run([sys.executable,"scripts/release_artifacts.py","version"],cwd=ROOT,check=True,text=True,capture_output=True); assert completed.stdout.strip()==VERSION
