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
        raise SystemExit(f"{path}: forbidden obsolete formal-contract tokens {present}")


def project_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit(f"{path}: project version not found")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = project_version(root / "pyproject.toml")

    require(
        root / "formal" / "AASMCalculus.tla",
        [
            "StageCandidate",
            "ActivateCandidate",
            "LearnSoft",
            "RegisterCertificate",
            "VerifyCertificate",
            "PromoteHard",
            "HardRequiresCertificate",
            "VerifiedRequiresRegistration",
            "HardComesFromSoft",
            "CandidateActivationIsAtomic",
            "FairnessProgress",
            "Restart",
            "TerminalStutter",
            "pendingCandidate = {}",
        ],
    )
    forbid(root / "formal" / "AASMCalculus.tla", ["LearnCertified =="])
    require(
        root / "formal" / "AASMCalculus.cfg",
        [
            "SPECIFICATION Spec",
            "HardRequiresCertificate",
            "VerifiedRequiresRegistration",
            "CandidateActivationIsAtomic",
            "FairnessProgress",
        ],
    )
    require(
        root / "formal" / "aasm_calculus.pml",
        [
            "soft_knowledge",
            "registered_certificate",
            "verified_certificate",
            "hard_knowledge",
            "HARD_REQUIRES_CERT",
            "VERIFIED_REQUIRES_REGISTRATION",
            "CANDIDATE_ATOMIC",
            "MAX_FAIRNESS_DEBT",
            "fairness_progress",
            "RESTART",
            "candidate_mask == 0 && !unresolved_mandatory",
        ],
    )

    require(
        root / "src" / "aasm" / "runtime_v24.py",
        [
            "def _commit_calculus",
            "def learn_constraint",
            'effective_strength = "SOFT"',
            "assert_hard_constraint_certification",
            "def promote_constraint_hard",
            "aasm_lineage",
            "supersedes_explanation_id",
        ],
    )
    require(
        root / "src" / "aasm" / "runtime_v23.py",
        [
            "def _stage_candidate_activation",
            "def _validate_calculus_state_for_commit",
            '"calculus": staged_calculus',
            '"candidate_state": state',
        ],
    )
    require(
        root / "src" / "aasm" / "assurance.py",
        [
            "NON_CONTIGUOUS_SEQUENCE",
            "PERSISTED_SNAPSHOT_MISMATCH",
            "assert_calculus_invariants",
            "hard_constraint_certification_issues",
        ],
    )
    require(
        root / "src" / "aasm" / "observability.py",
        ["def causal_graph", "def _closed_graph", "EXPOSE_OR_DISPOSITION"],
    )

    require(root / "pyproject.toml", ["reference_data/research/*.json", 'build==1.5.0'])
    require(
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"',
            'REMOTE_PROTOCOL_NAME = "aasm.remote.v1"',
            'REMOTE_PROTOCOL_VERSION = "0.19.0"',
            '"contract_id": "aasm.adoption.v1"',
            '"contract_version": "0.4.1"',
            '"source_distribution_self_test": True',
            '"source_distribution_scope": "FULL_REPOSITORY_CONTRACT"',
            '"historical_release_policy": "REPORT_ONLY"',
            '"docker compose up --build"',
            "run_research_synthesis_demo",
            "bootstrap_stack",
            "verify_stack",
            "def public_api_contract",
            "def validate_public_api_contract",
            "existing event/reducer runtime",
        ],
    )
    require(
        root / "src" / "aasm" / "research_demo.py",
        [
            "def verify_research_corpus",
            "def run_research_synthesis_demo",
            "LC-retrieval-only",
            "CERT-retrieval-only",
            "backjump_conflict",
            "user_interrupt",
            "check_durable_history",
            "engine.replay()",
        ],
    )
    require(
        root / "src" / "aasm" / "demo_stack.py",
        [
            "def bootstrap_stack",
            "def fresh_stack",
            "def complete_stack",
            "def verify_stack",
            "def run_worker_cycle",
            "RemoteWorkerLoop",
            "AASMRemoteClient",
            "engine.register_resource",
            "engine.schedule",
            "existing remote registration/claim/lease/completion API",
        ],
    )
    forbid(
        root / "src" / "aasm" / "demo_stack.py",
        ["DELETE FROM", "TRUNCATE", "UPDATE aasm_runs", "INSERT INTO aasm_runs"],
    )
    require(
        root / "compose.yaml",
        [
            "postgres:17-alpine",
            "bootstrap:",
            "runtime:",
            "worker-1:",
            "stackctl:",
            "aasm.demo_stack",
            "aasm.__version__",
        ],
    )
    forbid(root / "compose.yaml", ["DELETE FROM", "TRUNCATE"])

    require(
        root / "MANIFEST.in",
        [
            "recursive-include .github",
            "recursive-include docs",
            "recursive-include formal",
            "recursive-include profiles",
            "recursive-include schemas",
            "recursive-include scripts",
            "recursive-include tests",
        ],
    )
    require(
        root / "tests" / "test_v28_sdist_selfcontained.py",
        ["test_source_distribution_is_self_contained", "test_sdist_smoke.py"],
    )
    require(
        root / "tests" / "test_sdist_smoke.py",
        ["validate_public_api_contract", "execute_operator_runbook", "REPRESENTATIVE_MEMBERS"],
    )

    require(
        root / "README.md",
        [
            f"v{version}",
            "Models propose. AASM decides",
            "Canonical adoption surface",
            "aasm adoption-contract",
            "One-command start",
            "docker compose up --build",
            "Self-Contained Source Distribution",
            "v0.29.0 — Thin LangGraph Adapter",
        ],
    )
    require(
        root / "CHANGELOG.md",
        [
            f"## [{version}] -",
            "source distribution",
            "v0.28.1 assets are not overwritten",
            "aasm.adoption.v1",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental",
            "Program rule: extend the working path",
            "v0.28.2 — Self-Contained Source Distribution",
            "Current — implemented",
            "v0.29.0 — Thin LangGraph Adapter",
            "v0.34.0 — Distributed Recovery Certification",
            "Adoption scorecard",
        ],
    )
    require(
        root / "docs" / "ARCHITECTURE.md",
        ["Canonical adoption surface", "existing event/reducer runtime", "GET /adoption-contract"],
    )
    require(
        root / "docs" / "RESEARCH_SYNTHESIS_DEMO.md",
        ["existing event/reducer runtime", "aasm demo", "LC-retrieval-only", "exact replay"],
    )
    require(
        root / "docs" / "LOCAL_FULL_STACK.md",
        [
            "docker compose up --build",
            "stackctl fresh",
            "stackctl verify",
            "PostgreSQL 17",
            "No container mutates machine snapshots or AASM tables directly",
        ],
    )
    require(
        root / "docs" / "RELEASE_0.28.md",
        ["AASM v0.28.2", "standalone smoke test", "existing implementation path"],
    )
    require(
        root / ".github" / "workflows" / "formal.yml",
        [
            "MANIFEST.in",
            "tests/test_v28_sdist_selfcontained.py",
            "tests/test_sdist_smoke.py",
            "Verify bounded TLA+ model",
            "Verify bounded Promela model and fairness property",
        ],
    )

    print(
        "formal, runtime, release, adoption, hero-stack, local-stack, and self-contained-sdist source contracts: PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
