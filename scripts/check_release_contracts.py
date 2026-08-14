from pathlib import Path
import tomllib


def require(path, tokens):
    text = Path(path).read_text()
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.42.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v42"])
    require(root / "src/aasm/cli.py", ["cli_v42"])
    require(
        root / "src/aasm/public_v42.py",
        [
            '__version__ = "0.42.0"',
            '"contract_version": "0.18.0"',
            "aasm.reference-domains.v1",
            "REFERENCE_HARNESS_ONLY",
            '"kernel_changes"',
        ],
    )
    require(
        root / "src/aasm/reference_domains.py",
        [
            "aasm.reference-domains.v1",
            "constraint-solving",
            "software-repair",
            "research-synthesis",
            "formal-reasoning",
            "long-horizon-memory",
            "REFERENCE_HARNESS_ONLY",
            '"kernel_changes": "NONE"',
        ],
    )
    require(
        root / "src/aasm/cli_v42.py",
        ["reference-domain-contract", "reference-domain-stress"],
    )

    # v0.41 remains the active kernel runtime under the v0.42 harness/public layer.
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED"])
    require(
        root / "src/aasm/reuse_validation.py",
        [
            "subsumption_validator_required",
            "non_idempotent_effect_never_reused",
            "verification_strength_mismatch",
        ],
    )
    require(root / "src/aasm/_runtime_v41_reuse_records.py", ["def register_reuse_candidate", "def reuse_report", "self.add_evidence"])
    require(root / "src/aasm/_runtime_v41_reuse_commit.py", ["def commit_reuse_certificate", "self.add_evidence"])
    require(root / "src/aasm/_runtime_v41_solver.py", ["def solver_step", "SKIP_EXECUTION", "ROUTE_CAPABILITY"])

    require(
        root / "README.md",
        [
            "Current release — v0.42.0",
            "Reference Domains",
            "Next release:",
            "v0.43.0",
            "aasm.adoption.v1 / 0.18.0",
            "aasm.reference-domains.v1 / 0.1.0",
            "aasm.remote.v1 / 0.19.0",
        ],
    )
    require(
        root / "docs/CURRENT_RELEASE.md",
        [
            "AASM v0.42.0",
            "aasm.reference-domains.v1",
            "0.18.0",
            "runtime_v41",
            "v0.43",
        ],
    )
    require(
        root / "docs/REFERENCE_DOMAIN_STRESS.md",
        ["constraint-solving", "software-repair", "research-synthesis", "formal-reasoning", "long-horizon-memory"],
    )
    require(root / "tests/test_v42_reference_domains.py", ["0.42.0", "0.18.0", "reference-domain-stress"])

    for name in ("reuse-request.schema.json", "reuse-certificate.schema.json", "solver-step.schema.json", "reference-domain-stress-report.schema.json"):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.42 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
