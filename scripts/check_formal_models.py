from __future__ import annotations

from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing required formal-contract tokens {missing}")


def forbid(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden formal-contract tokens {present}")


def project_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit(f"{path}: project version not found")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = project_version(root / "pyproject.toml")
    if version != "0.31.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    require(root / "formal/AASMCalculus.tla", [
        'StageCandidate', 'ActivateCandidate', 'LearnSoft',
        'RegisterCertificate', 'VerifyCertificate', 'PromoteHard',
        'HardRequiresCertificate', 'CandidateActivationIsAtomic',
        'FairnessProgress', 'Restart', 'TerminalStutter',
    ])
    forbid(root / "formal/AASMCalculus.tla", ['LearnCertified =='])
    require(root / "formal/AASMCalculus.cfg", [
        'SPECIFICATION Spec', 'HardRequiresCertificate',
        'CandidateActivationIsAtomic', 'FairnessProgress',
    ])
    require(root / "formal/aasm_calculus.pml", [
        'soft_knowledge', 'registered_certificate', 'verified_certificate',
        'hard_knowledge', 'CANDIDATE_ATOMIC', 'fairness_progress',
    ])

    require(root / "formal/AASMScopeHierarchy.tla", [
        'OverrideA', 'BackjumpA', 'RestartA',
        'RootAuthorityRetained', 'StrategyAuthorityRetained',
        'PinnedParentRetained', 'CertifiedHardKnowledgeRetained',
        'LocalOverrideDoesNotMutateParent', 'SiblingBranchPreserved',
        'CausalBackjumpOnlyInvalidatesBranchA',
        'ScopedRestartPreservesParentsAndSiblings',
    ])
    require(root / "formal/AASMScopeHierarchy.cfg", [
        'SPECIFICATION Spec', 'HierarchyIsAcyclic',
        'CausalBackjumpOnlyInvalidatesBranchA',
        'ScopedRestartPreservesParentsAndSiblings',
    ])
    require(root / "formal/aasm_scope_hierarchy.pml", [
        'active[ROOT]', 'hard_knowledge', 'branch_b_active',
        'active[ARCH_B]', 'active[IMPL_B]', 'branch_a_active', 'restarted',
    ])

    require(root / "src/aasm/_calculus_logic.py", [
        'violated_hard_constraints', 'effective_scope_values', 'scope_active_models',
    ])
    require(root / "src/aasm/calculus.py", [
        'assert_scope_calculus_invariants', 'assert_calculus_invariants',
    ])
    require(root / "src/aasm/_runtime_v31_search.py", ['def _stage_candidate_activation'])
    require(root / "src/aasm/_runtime_v31_recovery.py", ['def backjump_conflict', 'def restart_scope', 'dependency_impacted_scopes'])
    require(root / "src/aasm/_scopes_projection.py", ['def effective_scope_decisions', 'def dependency_impacted_scopes'])
    require(root / "src/aasm/_scopes_graph.py", ['def validate_scope_state'])
    require(root / "src/aasm/_scopes_invariants.py", ['def assert_scope_calculus_invariants'])
    require(root / ".github/workflows/formal.yml", [
        'Verify bounded calculus and scope TLA+ models',
        'AASMScopeHierarchy.cfg', 'AASMScopeHierarchy.tla',
        'Verify bounded calculus and scope Promela models',
        'aasm_scope_hierarchy.pml',
    ])
    require(root / "docs/FORMAL_ASSURANCE.md", [
        'AASMScopeHierarchy.tla', 'pinned-parent', 'scoped restart',
    ])
    require(root / "README.md", [
        'v0.31.0', 'Hierarchical Decision Scopes',
        'v0.32.0 — Runtime/Formal Trace Conformance',
    ])
    print("formal calculus and v0.31 scope authority contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
