from __future__ import annotations

from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing release/readiness tokens {missing}")


def forbid(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden release/readiness tokens {present}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)
    version = str(project["project"]["version"])
    if version != "0.30.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(
        root / "pyproject.toml",
        [
            'setuptools==83.0.0', 'wheel==0.47.0', 'build==1.5.0',
            'jsonschema>=4.23', 'license = "MIT"',
            'license-files = ["LICENSE"]', 'langgraph = ["langgraph>=1.2,<2"]',
        ],
    )
    require(
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"', '"contract_version": "0.6.0"',
            '"contract_id": ADAPTER_CONFORMANCE_ID',
            '"contract_version": ADAPTER_CONFORMANCE_VERSION',
            '"required_scenarios": list(CONFORMANCE_SCENARIOS)',
            '"audit_boundary": "CONFORMANCE_HOOK_NOT_SANDBOX"',
            '"reproducible_builds": True', '"source_distribution_self_test": True',
            '"source_distribution_scope": "FULL_REPOSITORY_CONTRACT"',
            '"historical_release_policy": "REPORT_ONLY"',
        ],
    )

    integration_dir = root / "src" / "aasm" / "integrations"
    require(
        integration_dir / "conformance.py",
        [
            "class AdapterCapabilityDeclaration", "class AdapterConformanceReport",
            "class AdapterConformanceDriver", "class AuditedStore",
            "class AdapterConformanceKit", "DIRECT_STORAGE_WRITE",
            "DUPLICATE_OR_BYPASSED_AUTHORITY", "DURABLE_HISTORY_INVALID",
            "REPLAY_MISMATCH", "SCENARIO_UNSUPPORTED",
        ],
    )
    require(
        integration_dir / "conformance_registry.py",
        ["BUILTIN_CONFORMANCE_DRIVERS", "def list_conformance_drivers", "def run_adapter_conformance"],
    )
    require(
        integration_dir / "langgraph_conformance.py",
        [
            'LANGGRAPH_CONFORMANCE_DRIVER_ID = "aasm.langgraph.conformance.v1"',
            "class LangGraphConformanceDriver", "def capability_declaration", "def run_scenario",
        ],
    )
    require(
        root / "schemas" / "adapter-capability.schema.json",
        ['"title": "AASM Adapter Capability Declaration"', '"unknown_effect"', '"direct_storage_writes"'],
    )
    require(
        root / "schemas" / "adapter-conformance-report.schema.json",
        ['"const": "aasm.adapter.conformance.v1"', '"PASS"', '"INCONCLUSIVE"', '"report_fingerprint"'],
    )
    require(
        root / "tests" / "test_v30_adapter_conformance.py",
        [
            "test_langgraph_reference_driver_passes_all_required_scenarios",
            "test_direct_storage_write_is_rejected_even_when_functional_output_passes",
            "test_duplicate_machine_authority_declaration_is_rejected",
            "test_unsupported_required_scenario_is_inconclusive",
            "test_authenticated_http_runner_and_contract_endpoint",
        ],
    )

    require(
        root / "scripts" / "release_artifacts.py",
        ["release_artifacts_core", "release_artifacts_github", "release_artifacts_cli"],
    )
    require(
        root / "scripts" / "release_artifacts_core.py",
        [
            "def verify_wheel", "def verify_sdist", "def compare_builds",
            "def build_historical_release_report", "historical-release-report.json",
            "PENDING_OWNER_PUBLICATION",
        ],
    )
    require(
        root / "scripts" / "release_artifacts_github.py",
        ["def verify_release_asset_snapshot", "def verify_github_release"],
    )

    require(
        root / ".github" / "workflows" / "ci.yml",
        [
            "wheel_smoke:", "langgraph_integration:", "adapter_conformance:",
            "Install adapter conformance dependencies",
            "Run framework-neutral conformance and negative fixtures",
            "aasm adapter-conformance --adapter langgraph",
            "Build two byte-identical distributions", 'build==1.5.0', 'twine==6.2.0',
            "SOURCE_DATE_EPOCH", "compare-builds", "verify-wheel", "verify-sdist",
        ],
    )
    release_workflow = root / ".github" / "workflows" / "release.yml"
    require(
        release_workflow,
        [
            'workflows: ["CI"]', "should_release", "aasm/ci-summary",
            "aasm/formal-assurance", "Build and verify two byte-identical distributions",
            "historical-report", "verify-github-release", "gh release create",
            '--target "$COMMIT_SHA"', "SHA256SUMS.txt", "release-manifest.json",
            "pypa/gh-action-pypi-publish@release/v1", "AASM_PUBLISH_PYPI",
            "Adapter Conformance Kit", "docs/RELEASE_0.30.md",
        ],
    )
    forbid(
        release_workflow,
        ["--clobber", 'git push origin "refs/tags/', "git tag -a", "Backfill maintained historical source releases"],
    )
    require(
        root / ".github" / "workflows" / "formal.yml",
        [
            "docs/ADAPTER_CONFORMANCE.md", "docs/RELEASE_0.30.md",
            "schemas/adapter-capability.schema.json",
            "schemas/adapter-conformance-report.schema.json",
            "src/aasm/cli_v30.py", "src/aasm/control_center_v30.py",
            "src/aasm/runtime_v30.py", "src/aasm/server_v30.py",
            "tests/test_v30_adapter_conformance.py", "scripts/release_artifacts*.py",
        ],
    )
    require(
        root / "MANIFEST.in",
        [
            "include .gitignore .dockerignore", "recursive-include .github",
            "recursive-include docs", "recursive-include examples",
            "recursive-include formal", "recursive-include profiles",
            "recursive-include schemas", "recursive-include scripts", "recursive-include tests",
        ],
    )
    require(
        root / "tests" / "test_sdist_smoke.py",
        [
            "test_extracted_sdist_file_inventory_is_self_consistent",
            "scripts/release_manifest.py", "scripts/release_artifacts_core.py",
            "src/aasm/integrations/conformance.py",
            "tests/test_v30_adapter_conformance.py",
        ],
    )
    require(
        root / "README.md",
        [
            f"v{version}", "Adapter Conformance Kit",
            "aasm adapter-conformance --adapter langgraph",
            "aasm.adapter.conformance.v1 / 0.1.0",
            "PASS | FAIL | INCONCLUSIVE", "v0.31.0 — Hierarchical Decision Scopes",
            "aasm.remote.v1 / 0.19.0",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental", "v0.30.0 — Adapter Conformance Kit",
            "Current — implemented", "v0.31.0 — Hierarchical Decision Scopes",
            "v0.34.0 — Distributed Recovery Certification", "Adoption scorecard",
        ],
    )
    require(
        root / "CHANGELOG.md",
        [f"## [{version}] -", "aasm.adapter.conformance.v1 / 0.1.0", "CONFORMANCE_HOOK_NOT_SANDBOX"],
    )
    require(
        root / "docs" / "COMPATIBILITY.md",
        ["pre-1.0", "aasm.adoption.v1 / 0.6.0", "aasm.adapter.conformance.v1 / 0.1.0"],
    )
    require(
        root / "docs" / "RELEASE_PROCESS.md",
        [
            "Adapter conformance gate", "Standalone source-distribution gate",
            "PyPI Trusted Publisher", "never repairs an existing version",
        ],
    )
    require(
        root / "docs" / "RELEASE_0.30.md",
        [
            "AASM v0.30.0", "Adapter Conformance Kit",
            "existing event/reducer authority path", "v0.31.0 — Hierarchical Decision Scopes",
        ],
    )
    print("v0.30 adapter conformance, distribution, and release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
