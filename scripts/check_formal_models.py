from __future__ import annotations

from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing formal-contract tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.32.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic", "FairnessProgress"])
    require(root / "formal/AASMScopeHierarchy.tla", ["RootAuthorityRetained", "CausalBackjumpOnlyInvalidatesBranchA", "ScopedRestartPreservesParentsAndSiblings"])
    require(root / "formal/AASMTraceConformance.tla", ["NoDroppedPrefix", "SupportAligned", "UnknownExplicit", "KnownSupported"])
    require(root / "formal/aasm_trace_conformance.pml", ["projected", "UNSUPPORTED", "assert(count == 3)"])
    require(root / "src/aasm/trace_conformance.py", [
        'TRACE_CONTRACT_ID = "aasm.trace.v1"',
        'SEMANTIC_TRACE_CONTRACT_ID = "aasm.trace.semantic.v1"',
        "def project_trace", "def semantic_trace_check", "def build_trace_corpus",
        "UNSUPPORTED_TRANSITION", "source_event", "source_trace_sha256",
    ])
    require(root / "tests/test_v32_trace_conformance.py", [
        "test_lossless_projection_preserves_order_identity_and_digests",
        "test_unknown_transition_is_explicitly_unsupported_not_dropped",
        "test_semantic_counterexample_links_exact_source_event",
        "test_snapshot_only_input_is_rejected",
    ])
    require(root / ".github/workflows/formal.yml", [
        "Verify every bounded TLA+ model", "for cfg in *.cfg", "Verify every bounded Promela model", "for model in *.pml",
    ])
    print("v0.32 formal trace and inherited calculus/scope contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
