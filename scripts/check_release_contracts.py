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
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.31.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "pyproject.toml", [
        'version = "0.31.0"', 'setuptools==83.0.0', 'wheel==0.47.0',
        'build==1.5.0', 'jsonschema>=4.23', 'langgraph = ["langgraph>=1.2,<2"]',
    ])
    require(root / "src/aasm/__init__.py", [
        '__version__ = "0.31.0"', 'from .runtime_v31 import AASMEngine',
        '"contract_version": "0.7.0"', '"contract_id": SCOPE_CONTRACT_ID',
        '"contract_version": SCOPE_CONTRACT_VERSION', '"root_scope_id": ROOT_SCOPE_ID',
        '"source_distribution_self_test": True', '"historical_release_policy": "REPORT_ONLY"',
    ])
    require(root / "src/aasm/_scopes_model.py", ['SCOPE_CONTRACT_ID = "aasm.scopes.v1"', 'class DecisionScope', 'class ScopeDependency'])
    require(root / "src/aasm/_scopes_projection.py", ['def effective_scope_decisions', 'def dependency_impacted_scopes'])
    require(root / "src/aasm/_scopes_invariants.py", ['def assert_scope_calculus_invariants'])
    require(root / "src/aasm/runtime_v31.py", ['class AASMEngine('])
    require(root / "src/aasm/_runtime_v31_admin.py", ['def register_scope', 'def register_scope_dependency', 'def effective_scope_context', 'def migrate_legacy_scopes'])
    require(root / "src/aasm/_runtime_v31_recovery.py", ['def restart_scope', 'def backjump_conflict'])
    require(root / "src/aasm/_runtime_v31_search.py", ['def _stage_candidate_activation'])
    require(root / "src/aasm/_calculus_logic.py", ['scope_active_models', 'effective_scope_values', 'scoped_subject_key'])
    require(root / "src/aasm/calculus.py", ['assert_scope_calculus_invariants'])
    require(root / "src/aasm/cli_v31.py", [
        'scope-register', 'scope-dependency', 'scope-report',
        'scope-context', 'scope-restart', 'scope-migrate',
    ])
    require(root / "src/aasm/server_v31.py", [
        'parts[3] == "scopes"', 'engine.scope_report()', 'AASMEngine = AASMEngine',
    ])
    require(root / "src/aasm/control_center_v31.py", [
        'Hierarchical Decision Scopes', 'loadAasmScopes', 'effective_active_model',
    ])

    for schema, tokens in {
        "decision-scope.schema.json": ['"title": "AASM Decision Scope"', '"NEEDS_REVALIDATION"', '"override_policy"'],
        "scope-dependency.schema.json": ['"title": "AASM Scope Dependency"', '"upstream_scope_id"', '"REVALIDATE"'],
        "scope-report.schema.json": ['"title": "AASM Scope Report"', '"const": "aasm.scopes.v1"', '"legacy_flat_state_migrated"'],
    }.items():
        require(root / "schemas" / schema, tokens)

    require(root / "tests/test_v31_scopes.py", [
        'test_register_hierarchy_and_effective_inheritance',
        'test_cross_scope_backjump_invalidates_causal_branch_and_preserves_sibling',
        'test_scoped_restart_preserves_parent_sibling_and_pinned_decisions',
        'test_multi_scope_candidate_failure_commits_nothing',
    ])
    require(root / ".github/workflows/ci.yml", [
        'hierarchical_scopes:', 'tests/test_v31_scopes.py',
        'SCOPES_RESULT', 'Build two byte-identical distributions',
        'adapter_conformance:', 'langgraph_integration:', 'postgres_integration:', 'compose_smoke:',
    ])
    formal = root / ".github/workflows/formal.yml"
    require(formal, [
        'AASMScopeHierarchy.cfg', 'AASMScopeHierarchy.tla',
        'aasm_scope_hierarchy.pml', 'tests/test_v31_scopes.py',
        'src/aasm/runtime_v31.py', 'src/aasm/_runtime_v31_*.py', 'src/aasm/scopes.py', 'src/aasm/_scopes_*.py',
    ])
    release = root / ".github/workflows/release.yml"
    require(release, [
        'workflows: ["CI"]', 'aasm/ci-summary', 'aasm/formal-assurance',
        'Build and verify two byte-identical distributions', 'verify-github-release',
        'gh release create', '--target "$COMMIT_SHA"',
        'Hierarchical Decision Scopes', 'docs/RELEASE_0.31.md',
        'pypa/gh-action-pypi-publish@release/v1',
    ])
    forbid(release, ['--clobber', 'git tag -a', 'git push origin "refs/tags/'])

    require(root / "README.md", [
        'v0.31.0', 'Hierarchical Decision Scopes', 'aasm.scopes.v1 / 0.1.0',
        'aasm.adoption.v1 / 0.7.0', 'v0.32.0 — Runtime/Formal Trace Conformance',
        'aasm.remote.v1 / 0.19.0',
    ])
    require(root / "ROADMAP.md", [
        'v0.31.0 / experimental', 'Current — implemented',
        'v0.32.0 — Runtime/Formal Trace Conformance',
        'v0.35.0 — Semantic Problem Model Foundations',
        'v0.45.0 — Semantic Solver Release Candidate',
        'ProblemDefinition', 'Semantic Dependency Graph', 'Adoption scorecard',
    ])
    require(root / "CHANGELOG.md", [
        '## [0.31.0] -', 'aasm.scopes.v1 / 0.1.0',
        'one authoritative machine', 'v0.32.0 Runtime/Formal Trace Conformance',
    ])
    require(root / "docs/HIERARCHICAL_DECISION_SCOPES.md", [
        'one authoritative machine', 'Causal branch recovery',
        'Atomic multi-scope candidates', 'scope-migrate',
    ])
    require(root / "docs/COMPATIBILITY.md", [
        '0.31.0', 'aasm.adoption.v1 / 0.7.0', 'aasm.scopes.v1 / 0.1.0',
    ])
    require(root / "docs/RELEASE_PROCESS.md", [
        'Hierarchical scope gate', 'Standalone source-distribution gate',
        'PyPI Trusted Publisher', 'never repairs an existing version',
    ])
    require(root / "docs/RELEASE_0.31.md", [
        'AASM v0.31.0', 'Hierarchical Decision Scopes',
        'existing event creation', 'v0.32.0 — Runtime/Formal Trace Conformance',
    ])
    print("v0.31 hierarchical scopes, distribution, and release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
