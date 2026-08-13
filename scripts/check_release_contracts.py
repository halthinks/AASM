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
    if version != "0.32.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "pyproject.toml", ['version = "0.32.0"', 'build==1.5.0', 'jsonschema>=4.23', 'langgraph>=1.2,<2'])
    require(root / "src/aasm/__init__.py", [
        '__version__ = "0.32.0"', 'from .runtime_v32 import AASMEngine', '"contract_version": "0.8.0"',
        'TRACE_CONTRACT_ID', 'SEMANTIC_TRACE_CONTRACT_ID', '"snapshot_only_input": "REJECTED"',
    ])
    require(root / "src/aasm/runtime_v32.py", ["class AASMEngine(V31Engine)", "def trace_projection", "def semantic_trace_report"])
    require(root / "src/aasm/cli_v32.py", ["trace-project", "trace-check", "trace-semantic"])
    require(root / "README.md", [
        "v0.32.0 — Runtime/Formal Trace Conformance", "aasm.trace.v1 / 0.1.0",
        "aasm.trace.semantic.v1 / 0.1.0", "v0.33.0 — Signed Provenance and Verifiable Exports",
    ])
    require(root / "ROADMAP.md", [
        "v0.32.0 — Runtime/Formal Trace Conformance", "Current — implemented",
        "v0.33.0 — Signed Provenance and Verifiable Exports", "v0.35.0 — Semantic Problem Model Foundations",
        "v0.36.0 — Semantic Compiler SDK", "Semantic Dependency Graph", "Adoption scorecard",
    ])
    require(root / "CHANGELOG.md", ["## [0.32.0] -", "aasm.trace.v1 / 0.1.0", "snapshot-only input"])
    require(root / "docs/TRACE_CONFORMANCE.md", ["Lossless projection", "Snapshot-only input", "Semantic witness checks", "INCONCLUSIVE"])
    require(root / "docs/RELEASE_0.32.md", ["AASM v0.32.0", "v0.33.0 — Signed Provenance and Verifiable Exports"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.32.0", "Runtime/Formal Trace Conformance"])
    for schema in ("trace-contract.schema.json", "trace-projection.schema.json", "semantic-trace-report.schema.json", "trace-corpus.schema.json"):
        if not (root / "schemas" / schema).is_file():
            raise SystemExit(f"missing schema: {schema}")
    release = root / ".github/workflows/release.yml"
    require(release, [
        'workflows: ["CI"]', "aasm/ci-summary", "aasm/formal-assurance", "compare-builds",
        'gh release create "$TAG"', '--target "$COMMIT_SHA"', '--notes-file docs/CURRENT_RELEASE.md',
        "verify-github-release", "SHA256SUMS.txt", "pypa/gh-action-pypi-publish@release/v1",
    ])
    forbid(release, ["--clobber", "git tag -a", 'git push origin "refs/tags/'])
    print("v0.32 trace, distribution, documentation, and release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
