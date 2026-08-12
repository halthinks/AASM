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
            "def learn_constraint",
            'effective_strength = "SOFT"',
            "assert_hard_constraint_certification",
            "def promote_constraint_hard",
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

    integration_dir = root / "src" / "aasm" / "integrations"
    require(
        integration_dir / "_langgraph_types.py",
        [
            'LANGGRAPH_ADAPTER_ID = "aasm.langgraph.v1"',
            'LANGGRAPH_ADAPTER_VERSION = "0.1.0"',
            "class LangGraphRunKey",
            "class LangGraphBinding",
            "class LangGraphRecoveryAction",
        ],
    )
    require(
        integration_dir / "_langgraph_binding.py",
        [
            "canonical AASM machine",
            "engine.register_decision",
            "engine.register_obligation",
            "engine.add_evidence",
            "engine.propose_effect",
            "from .. import AASMEngine as engine_class",
        ],
    )
    require(
        integration_dir / "_langgraph_conflict.py",
        [
            "engine.raise_conflict",
            "engine.register_explanation",
            "engine.learn_constraint",
            "engine.register_projection_certificate",
            "engine.verify_projection_certificate",
            "engine.promote_constraint_hard",
            "engine.backjump_conflict",
            "engine.restart_search",
            "engine.fork",
        ],
    )
    require(
        integration_dir / "langgraph.py",
        ["routing, or checkpoints", "class LangGraphAdapter", "def wrap_node(", "return result"],
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
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"',
            'REMOTE_PROTOCOL_NAME = "aasm.remote.v1"',
            'REMOTE_PROTOCOL_VERSION = "0.19.0"',
            '"contract_id": "aasm.adoption.v1"',
            '"contract_version": "0.5.0"',
            '"checkpoint_authority": "LANGGRAPH"',
            '"machine_authority": "AASM_EVENT_HISTORY"',
            '"source_distribution_self_test": True',
            "def public_api_contract",
            "def validate_public_api_contract",
        ],
    )
    require(
        root / "src" / "aasm" / "runtime_v29.py",
        ["class AASMEngine", "def langgraph_report", "def integration_report"],
    )
    require(
        root / "src" / "aasm" / "demo_stack.py",
        [
            "def bootstrap_stack",
            "def verify_stack",
            "RemoteWorkerLoop",
            "existing remote registration/claim/lease/completion API",
        ],
    )
    forbid(
        root / "src" / "aasm" / "demo_stack.py",
        ["DELETE FROM", "TRUNCATE", "UPDATE aasm_runs", "INSERT INTO aasm_runs"],
    )
    require(
        root / "compose.yaml",
        ["postgres:17-alpine", "runtime:", "worker-1:", "stackctl:", "aasm.__version__"],
    )
    forbid(root / "compose.yaml", ["DELETE FROM", "TRUNCATE"])

    require(
        root / "README.md",
        [
            f"v{version}",
            "Models propose. AASM decides",
            "Canonical adoption surface",
            "Thin LangGraph Adapter",
            "v0.30.0 — Adapter Conformance Kit",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental",
            "Program rule: extend the working path",
            "v0.29.0 — Thin LangGraph Adapter",
            "Current — implemented",
            "Adoption scorecard",
        ],
    )
    require(
        root / "docs" / "LANGGRAPH_ADAPTER.md",
        [
            "LangGraph application",
            "public AASM API",
            "configurable.thread_id",
            "Contradiction and learned no-good",
            "Non-goals",
        ],
    )
    require(
        root / "tests" / "test_v29_langgraph_adapter.py",
        [
            "preserve_unrelated_work",
            "violates learned hard constraints",
            "replay_snapshot_hash",
            "real LangGraph contract",
        ],
    )
    require(
        root / ".github" / "workflows" / "formal.yml",
        [
            "src/aasm/integrations/**",
            "tests/test_v29_langgraph_adapter.py",
            "Verify bounded TLA+ model",
            "Verify bounded Promela model and fairness property",
        ],
    )

    print("formal calculus and v0.29 adapter authority source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
