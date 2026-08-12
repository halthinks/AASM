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
    if version != "0.29.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(
        root / "pyproject.toml",
        [
            'setuptools==83.0.0',
            'wheel==0.47.0',
            'build==1.5.0',
            'jsonschema>=4.23',
            'license = "MIT"',
            'license-files = ["LICENSE"]',
            'langgraph = ["langgraph>=1.2,<2"]',
        ],
    )
    require(
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"',
            '"contract_version": "0.5.0"',
            '"adapter_id": LANGGRAPH_ADAPTER_ID',
            '"adapter_version": LANGGRAPH_ADAPTER_VERSION',
            '"checkpoint_authority": "LANGGRAPH"',
            '"machine_authority": "AASM_EVENT_HISTORY"',
            '"reproducible_builds": True',
            '"source_distribution_self_test": True',
            '"source_distribution_scope": "FULL_REPOSITORY_CONTRACT"',
            '"historical_release_policy": "REPORT_ONLY"',
        ],
    )

    integration_dir = root / "src" / "aasm" / "integrations"
    require(
        integration_dir / "_langgraph_types.py",
        [
            'LANGGRAPH_ADAPTER_ID = "aasm.langgraph.v1"',
            'LANGGRAPH_ADAPTER_VERSION = "0.1.0"',
            "class LangGraphRunKey",
            "class LangGraphBinding",
            "class LangGraphRecoveryAction",
            "configurable.thread_id",
            "LangGraph interrupt()",
        ],
    )
    require(
        integration_dir / "_langgraph_binding.py",
        [
            "class LangGraphBindingMixin",
            "def bind(",
            "def record_decision(",
            "def record_obligation(",
            "def record_evidence(",
            "def authorize_effect(",
            "AASM_EVENT_HISTORY",
            "from .. import AASMEngine as engine_class",
        ],
    )
    require(
        integration_dir / "_langgraph_conflict.py",
        ["class LangGraphConflictMixin", "def record_conflict(", "def recover("],
    )
    require(
        integration_dir / "langgraph.py",
        ["class LangGraphAdapter", "def wrap_node("],
    )
    for integration_path in integration_dir.glob("*langgraph*.py"):
        forbid(
            integration_path,
            [
                "DELETE FROM",
                "TRUNCATE",
                "INSERT INTO aasm_",
                "UPDATE aasm_",
                "store.append(",
                "patch_snapshot(",
                "from ..runtime_",
            ],
        )
    require(
        root / "src" / "aasm" / "runtime_v29.py",
        ["def langgraph_report", "def integration_report", 'surface == "langgraph"'],
    )
    require(
        root / "src" / "aasm" / "cli_v29.py",
        ["langgraph-binding", "LangGraphAdapter", '"integrations", "langgraph"'],
    )
    require(
        root / "src" / "aasm" / "control_center_v29.py",
        ["v0.29 Thin LangGraph Adapter", "/inspect/langgraph", "Adapted run"],
    )
    require(
        root / "src" / "aasm" / "server_v29.py",
        ["AASMEngine", "html_document", "make_handler = _v27.make_handler"],
    )
    require(
        root / "examples" / "langgraph_adoption.py",
        [
            "StateGraph",
            "ordinary_output",
            "governed_output",
            "unrelated_cache_preserved",
            "failed_combination_blocked_on_reuse",
            "exact_replay",
        ],
    )
    require(
        root / "tests" / "test_v29_langgraph_adapter.py",
        [
            "test_thread_binding_is_deterministic_idempotent_and_authoritative",
            "test_real_langgraph_stategraph_adopts_aasm_without_graph_rewrite",
            "test_decision_mapping_conflict_learning_backjump_and_reuse_preserve_unrelated_work",
            "test_runtime_cli_server_and_control_center_expose_langgraph_boundary",
        ],
    )
    require(
        root / "schemas" / "langgraph-binding.schema.json",
        ['"const": "aasm.langgraph.v1"', '"binding_scope"', '"THREAD"', '"RUN"'],
    )
    require(
        root / "schemas" / "langgraph-recovery.schema.json",
        ['"BACKJUMP"', '"PAUSE"', '"RESTART"', '"FORK"'],
    )

    require(
        root / "scripts" / "release_artifacts.py",
        ["release_artifacts_core", "release_artifacts_github", "release_artifacts_cli"],
    )
    require(
        root / "scripts" / "release_artifacts_core.py",
        [
            "def verify_wheel",
            "def verify_sdist",
            "def compare_builds",
            "def build_historical_release_report",
            "historical-release-report.json",
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
            "wheel_smoke:",
            "langgraph_integration:",
            "Install LangGraph integration extra",
            "examples/langgraph_adoption.py",
            "Build two byte-identical distributions",
            'build==1.5.0',
            'twine==6.2.0',
            "SOURCE_DATE_EPOCH",
            "compare-builds",
            "verify-wheel",
            "verify-sdist",
        ],
    )
    release_workflow = root / ".github" / "workflows" / "release.yml"
    require(
        release_workflow,
        [
            'workflows: ["CI"]',
            "should_release",
            "aasm/ci-summary",
            "aasm/formal-assurance",
            "Build and verify two byte-identical distributions",
            "historical-report",
            "verify-github-release",
            "gh release create",
            '--target "$COMMIT_SHA"',
            "SHA256SUMS.txt",
            "release-manifest.json",
            "pypa/gh-action-pypi-publish@release/v1",
            "AASM_PUBLISH_PYPI",
            "Thin LangGraph Adapter",
            "docs/RELEASE_0.29.md",
        ],
    )
    forbid(
        release_workflow,
        [
            "--clobber",
            'git push origin "refs/tags/',
            "git tag -a",
            "Backfill maintained historical source releases",
        ],
    )
    require(
        root / ".github" / "workflows" / "formal.yml",
        [
            "docs/LANGGRAPH_ADAPTER.md",
            "docs/RELEASE_0.29.md",
            "src/aasm/integrations/**",
            "tests/test_v29_langgraph_adapter.py",
            "tests/test_v28_sdist_selfcontained.py",
            "tests/test_sdist_smoke.py",
            "scripts/release_artifacts*.py",
        ],
    )
    require(
        root / "MANIFEST.in",
        [
            "include .gitignore .dockerignore",
            "recursive-include .github",
            "recursive-include docs",
            "recursive-include examples",
            "recursive-include formal",
            "recursive-include profiles",
            "recursive-include schemas",
            "recursive-include scripts",
            "recursive-include tests",
        ],
    )
    require(
        root / "tests" / "test_sdist_smoke.py",
        [
            "test_extracted_sdist_file_inventory_is_self_consistent",
            "scripts/release_manifest.py",
            "scripts/release_artifacts_core.py",
            "scripts/release_artifacts_github.py",
            "scripts/release_artifacts_cli.py",
            "src/aasm/integrations/langgraph.py",
        ],
    )
    require(
        root / "README.md",
        [
            f"v{version}",
            "Thin LangGraph Adapter",
            "pip install 'aasm-runtime[langgraph]'",
            "aasm langgraph-binding",
            "v0.30.0 — Adapter Conformance Kit",
            "aasm.remote.v1 / 0.19.0",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental",
            "v0.29.0 — Thin LangGraph Adapter",
            "Current — implemented",
            "v0.30.0 — Adapter Conformance Kit",
            "v0.34.0 — Distributed Recovery Certification",
        ],
    )
    require(
        root / "CHANGELOG.md",
        [f"## [{version}] -", "aasm.langgraph.v1 / 0.1.0", "framework-private AASM truth"],
    )
    require(
        root / "docs" / "COMPATIBILITY.md",
        ["pre-1.0", "aasm.adoption.v1 / 0.5.0", "aasm.langgraph.v1 / 0.1.0"],
    )
    require(
        root / "docs" / "RELEASE_PROCESS.md",
        [
            "Standalone source-distribution gate",
            "Optional framework-adapter gate",
            "PyPI Trusted Publisher",
            "never repairs an existing version",
        ],
    )
    require(
        root / "docs" / "RELEASE_0.29.md",
        [
            "AASM v0.29.0",
            "Thin LangGraph Adapter",
            "existing event/reducer authority path",
            "v0.30.0 — Adapter Conformance Kit",
        ],
    )
    print("v0.29 thin LangGraph adapter, self-contained distribution, and release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
