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
    if version != "0.43.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v43"])
    require(root / "src/aasm/cli.py", ["cli_v43"])
    require(
        root / "src/aasm/public_v43.py",
        [
            '__version__ = "0.43.0"',
            '"contract_version": "0.19.0"',
            "CERTIFICATION_CONTRACT_ID",
            "SII_CONTRACT_ID",
            "CERTIFICATION_HARNESS_ONLY",
            "V0.41_ENGINE_UNCHANGED",
        ],
    )
    require(
        root / "src/aasm/certification.py",
        [
            "aasm.certification.v1",
            "PASS",
            "FAIL",
            "INCONCLUSIVE",
            "reference-domains",
            "solver-reuse",
            "truth-memory",
            "formal-verification",
            "sii-preview",
            "missing_evidence_is_not_pass",
            "self_attestation_is_not_certification",
        ],
    )
    require(
        root / "src/aasm/sii.py",
        [
            "aasm.sii.v1",
            "EXPERIMENTAL_CERTIFICATION_TARGET",
            "The reasoner proposes; AASM measures.",
            "Utility may buy resources; utility never buys truth.",
            "CALLER_ASSERTED_PREVIEW_V043",
            "POLICY_PROJECTION_ONLY_V043",
            "measurement_principal_authority_binding",
            "resource_lease_scheduler_enforcement",
            "authority_reward",
            "NEVER",
        ],
    )
    require(
        root / "src/aasm/cli_v43.py",
        ["certification-contract", "certify", "sii-contract"],
    )

    # v0.41 remains the active kernel runtime under v0.43 certification/SII preview surfaces.
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED"])
    require(
        root / "src/aasm/reuse_validation.py",
        ["subsumption_validator_required", "non_idempotent_effect_never_reused", "verification_strength_mismatch"],
    )
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", '"kernel_changes": "NONE"'])
    require(root / "src/aasm/_runtime_v41_solver.py", ["def solver_step", "SKIP_EXECUTION", "ROUTE_CAPABILITY"])

    require(
        root / "README.md",
        [
            "Current release — v0.43.0",
            "Semantic Conformance",
            "PASS | FAIL | INCONCLUSIVE",
            "Next release:",
            "v0.44.0",
            "Symbiotic Intelligence Interface",
            "aasm.adoption.v1 / 0.19.0",
            "aasm.certification.v1 / 0.1.0",
            "aasm.sii.v1 / 0.2.0",
            "aasm.reference-domains.v1 / 0.1.0",
            "aasm.remote.v1 / 0.19.0",
        ],
    )
    require(
        root / "docs/CURRENT_RELEASE.md",
        [
            "AASM v0.43.0",
            "aasm.certification.v1",
            "aasm.sii.v1",
            "0.19.0",
            "runtime_v41",
            "v0.44",
        ],
    )
    require(root / "docs/SEMANTIC_CERTIFICATION.md", ["PASS", "FAIL", "INCONCLUSIVE", "SII preview", "core_status"])
    require(root / "docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md", ["ResourceLease", "graduation gates", "runtime_v41.AASMEngine"])
    require(root / "tests/test_v43_certification.py", ["0.43.0", "0.19.0", "INCONCLUSIVE", "sii-preview"])

    for name in (
        "reuse-request.schema.json",
        "reuse-certificate.schema.json",
        "solver-step.schema.json",
        "reference-domain-stress-report.schema.json",
        "certification-report.schema.json",
        "sii-proposal.schema.json",
        "sii-outcome.schema.json",
        "sii-resource-lease.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.43 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
