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
    tla = root / "formal" / "AASMCalculus.tla"
    cfg = root / "formal" / "AASMCalculus.cfg"
    promela = root / "formal" / "aasm_calculus.pml"

    require(
        tla,
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
    forbid(tla, ["LearnCertified =="])
    require(
        cfg,
        [
            "SPECIFICATION Spec",
            "HardRequiresCertificate",
            "VerifiedRequiresRegistration",
            "CandidateActivationIsAtomic",
            "FairnessProgress",
        ],
    )
    require(
        promela,
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
            "effective_strength = \"SOFT\"",
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
            "\"calculus\": staged_calculus",
            "\"candidate_state\": state",
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

    version = project_version(root / "pyproject.toml")
    require(root / "pyproject.toml", ["reference_data/research/*.json"])
    require(
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"',
            'REMOTE_PROTOCOL_NAME = "aasm.remote.v1"',
            'REMOTE_PROTOCOL_VERSION = "0.19.0"',
            "PUBLIC_API_CONTRACT",
            '"contract_id": "aasm.adoption.v1"',
            '"reference_application"',
            '"local_stack"',
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
        root / "src" / "aasm" / "cli_v25.py",
        [
            "adoption-contract",
            "validate_public_api_contract",
            '"research-synthesis"',
            "run_research_synthesis_demo",
            'commands.choices["demo"]',
        ],
    )
    require(
        root / "src" / "aasm" / "cli_v27.py",
        [
            "execute_stack_action",
            'commands.add_parser(\n        "stack"',
            'serve_command.add_argument(\n        "--demo-state"',
            "server_v27",
        ],
    )
    require(
        root / "src" / "aasm" / "server_v25.py",
        [
            'server_version = f"AASM/{__version__}"',
            'if self.path == "/adoption-contract"',
            '"runtime_version": __version__',
            "REMOTE_PROTOCOL_VERSION",
        ],
    )
    require(
        root / "src" / "aasm" / "server_v27.py",
        [
            "_v19.html_document = html_document",
            'if parsed.path == "/"',
            'if parsed.path == "/demo-stack"',
            "demo_state_path",
            "AASM refuses non-loopback binding without --token",
        ],
    )
    require(
        root / "src" / "aasm" / "research_profile.py",
        [
            "def research_profile",
            "def research_package",
            'profile_id="aasm.research-synthesis"',
            "ResearchProfileRegistry",
            '"hero_profile": True',
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
            "run_research_synthesis_demo",
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
        root / "src" / "aasm" / "control_center_v26.py",
        [
            "v19_html_document",
            "Decision Graph",
            "Obligation Graph",
            "Evidence Graph",
            "learned no-good",
            "/inspect/conflicts",
        ],
    )
    require(
        root / "src" / "aasm" / "control_center_v27.py",
        [
            "v26_html_document",
            "v0.27 One-Command Local Full Stack",
            "Live setup machine",
            "Completed reference run",
            "/demo-stack",
            "aasmStackAutoload",
        ],
    )
    require(
        root / "src" / "aasm" / "reference_data" / "research" / "manifest.json",
        [
            '"corpus_id": "aasm-research-corpus-v1"',
            '"network_required": false',
            '"model_key_required": false',
            '"synthetic": true',
        ],
    )
    require(
        root / "profiles" / "research" / "profile.json",
        [
            '"profile_id": "aasm.research-synthesis"',
            '"profile_version": "1.0.0"',
            '"hero_profile": true',
        ],
    )
    require(
        root / "Dockerfile",
        [
            "FROM python:3.13-slim",
            "python -m pip install '.[postgres]'",
            "EXPOSE 8787",
        ],
    )
    require(
        root / "compose.yaml",
        [
            "postgres:17-alpine",
            "bootstrap:",
            "runtime:",
            "worker-1:",
            "worker-2:",
            "stackctl:",
            "service_completed_successfully",
            "aasm.demo_stack",
            "two-workers",
        ],
    )
    forbid(root / "compose.yaml", ["DELETE FROM", "TRUNCATE"])
    require(
        root / "README.md",
        [
            f"v{version}",
            "Models propose. AASM decides",
            "Canonical adoption surface",
            "aasm adoption-contract",
            "One-command start",
            "docker compose up --build",
            "v0.28.0 — Distribution and Operator Readiness",
        ],
    )
    require(
        root / "CHANGELOG.md",
        [
            f"## [{version}] -",
            "One-command local stack",
            "Research Synthesis Hero Stack",
            "aasm.adoption.v1",
            "parallel runtime",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental",
            "Program rule: extend the working path",
            "v0.27.0 — One-Command Local Full Stack",
            "Current — implemented",
            "v0.28.0 — Distribution and Operator Readiness",
            "Adoption scorecard",
        ],
    )
    require(
        root / "docs" / "ARCHITECTURE.md",
        [
            "Canonical adoption surface",
            "existing event/reducer runtime",
            "GET /adoption-contract",
        ],
    )
    require(
        root / "docs" / "RESEARCH_SYNTHESIS_DEMO.md",
        [
            "existing event/reducer runtime",
            "aasm demo",
            "LC-retrieval-only",
            "exact replay",
        ],
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
        root / "docs" / "RELEASE_0.27.md",
        [
            "AASM v0.27.0",
            "One-Command Local Full Stack",
            "existing event/reducer authority path",
            "Docker Compose end-to-end smoke test",
        ],
    )
    require(
        root / "WHY_AASM.md",
        [
            "Stateless retry baseline",
            "AASM reference run",
            "Failed interpretation blocked from recurring",
        ],
    )
    require(
        root / "tests" / "test_v26_research_synthesis.py",
        [
            "test_complete_reference_run_demonstrates_learning_backjump_and_preservation",
            "test_control_center_extends_existing_dashboard_with_reasoning_surfaces",
        ],
    )
    require(
        root / "tests" / "test_v27_local_stack.py",
        [
            "test_stack_bootstrap_seeds_live_and_completed_canonical_machines",
            "test_demo_worker_uses_existing_remote_registration_claim_and_lease_path",
            "test_fresh_is_a_non_destructive_canonical_reset",
            "test_compose_and_control_center_expose_the_documented_stack_contract",
        ],
    )

    print(
        "formal, runtime, release, adoption, hero-stack, and local-full-stack source contracts: PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
