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

    require(
        root / "src" / "aasm" / "__init__.py",
        [
            f'__version__ = "{version}"',
            '"contract_version": "0.4.0"',
            '"distribution"',
            '"operator_runbooks"',
            '"runbook"',
            "execute_operator_runbook",
        ],
    )
    require(
        root / "src" / "aasm" / "runbook_common.py",
        ["class OperatorRunbookResult", "RUNBOOK_DEFINITIONS", "def list_operator_runbooks"],
    )
    runbook_sources = {
        "runbook_lease.py": ["def run_lease_loss_recovery", "AASMEngine"],
        "runbook_requirement.py": ["def run_requirement_change", "user_interrupt"],
        "runbook_learning.py": ["def run_learned_no_good", "run_research_synthesis_demo"],
        "runbook_approval.py": ["def run_human_approval", "QuorumAuthority"],
        "runbook_replay.py": ["def run_replay_fork", "engine.fork"],
        "runbook_effect.py": ["def run_unknown_effect", "EffectUnknownOutcome"],
        "runbook_history.py": ["def run_history_diagnosis", "NON_CONTIGUOUS_SEQUENCE"],
    }
    for name, tokens in runbook_sources.items():
        require(root / "src" / "aasm" / name, tokens)
        forbid(
            root / "src" / "aasm" / name,
            ["DELETE FROM", "TRUNCATE", "UPDATE aasm_runs", "INSERT INTO aasm_runs"],
        )
    require(
        root / "src" / "aasm" / "operator_runbooks.py",
        ["RUNBOOK_HANDLERS", "def execute_operator_runbook"],
    )
    require(
        root / "src" / "aasm" / "cli_v28.py",
        ["execute_operator_runbook", "list_operator_runbooks", '"runbook"'],
    )
    require(
        root / "scripts" / "release_artifacts.py",
        [
            "def verify_wheel",
            "def verify_sdist",
            "def verify_release_history",
            "sha256_file",
            "release-manifest.json",
        ],
    )
    require(
        root / ".github" / "workflows" / "ci.yml",
        [
            "wheel_smoke:",
            "python -m build",
            "verify-wheel",
            "verify-sdist",
            "aasm runbook history-diagnosis",
        ],
    )
    release_workflow = root / ".github" / "workflows" / "release.yml"
    require(
        release_workflow,
        [
            'workflows: ["CI"]',
            "aasm/formal-assurance",
            "gh release create",
            '--target "$COMMIT_SHA"',
            "tag_commit()",
            "SHA256SUMS.txt",
            "release-manifest.json",
            "pypa/gh-action-pypi-publish@release/v1",
            "AASM_PUBLISH_PYPI",
        ],
    )
    forbid(release_workflow, ["git push origin \"refs/tags/", "git tag -a"])
    require(
        root / "README.md",
        [
            f"v{version}",
            "Distribution and Operator Readiness",
            "pip install aasm-runtime",
            "Operator runbooks",
            "aasm runbook unknown-effect",
            "v0.29.0 — Thin LangGraph Adapter",
            "aasm.remote.v1 / 0.19.0",
        ],
    )
    require(
        root / "ROADMAP.md",
        [
            f"v{version} / experimental",
            "v0.28.0 — Distribution and Operator Readiness",
            "Current — implemented",
            "v0.29.0 — Thin LangGraph Adapter",
            "Adoption scorecard",
        ],
    )
    require(
        root / "CHANGELOG.md",
        [f"## [{version}] -", "Operator runbooks", "Trusted Publisher"],
    )
    require(
        root / "docs" / "COMPATIBILITY.md",
        ["pre-1.0", "aasm.adoption.v1", "immutable release tag"],
    )
    require(
        root / "docs" / "RELEASE_PROCESS.md",
        [
            "PyPI Trusted Publisher",
            "AASM_PUBLISH_PYPI",
            "clean virtual environment",
            "GitHub Release API",
        ],
    )
    require(
        root / "docs" / "RELEASE_0.28.md",
        ["AASM v0.28.0", "existing event/reducer authority path", "Seven executable runbooks"],
    )
    runbooks = {
        "lease-loss": "Recover after lease loss",
        "requirement-change": "Inject a requirement without destroying the plan",
        "learned-no-good": "Inspect and act on a learned no-good",
        "human-approval": "Run a human approval gate with policy as data",
        "replay-fork": "Safely replay and fork a machine",
        "unknown-effect": "Reconcile an UNKNOWN external effect",
        "history-diagnosis": "Diagnose a failed durable-history verification",
    }
    for runbook_id, title in runbooks.items():
        require(
            root / "docs" / "runbooks" / f"{runbook_id}.md",
            [title, f"aasm runbook {runbook_id}", "Failure indicators", "Reset"],
        )
    require(
        root / "tests" / "test_v28_operator_runbooks.py",
        ["test_each_operator_runbook_is_an_executable_passing_drill"],
    )
    require(
        root / "tests" / "test_v28_distribution.py",
        ["test_release_workflow_builds_verifies_releases_and_gates_pypi"],
    )
    print("distribution, immutable-release, compatibility, and operator-runbook contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
