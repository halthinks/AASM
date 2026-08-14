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
    if version != "0.45.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMSemanticTruthMaintenance.tla", ["AffectedDescendantsOnly", "UnrelatedSiblingPreserved"])
    require(root / "formal/AASMTypedCapabilities.tla", ["SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/AASMHierarchicalMemory.tla", ["StaleSemanticMemoryExcluded", "DerivedIndexCannotChangeMemoryIdentity"])
    require(root / "formal/AASMReusePlane.tla", ["SkipRequiresCertificate", "CertificateRequiresValidation", "CacheDeletionDoesNotDefineTruth"])
    require(root / "formal/AASMOptimizationPortfolio.tla", ["ResultRequiresLease", "ResultIsEvidence", "SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/aasm_optimization_portfolio.pml", ["task_leased", "result_evidence", "policy_acted", "truth_authorized"])

    require(root / "src/aasm/reuse_model.py", ["INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED", "OPTIMIZATION_RESULT"])
    require(root / "src/aasm/reuse_validation.py", ["non_idempotent_effect_never_reused", "subsumption_validator_required", "verification_strength_mismatch"])
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", "kernel_changes"])
    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "CERTIFICATION_HARNESS_ONLY", "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM", "INCONCLUSIVE"])
    require(root / "src/aasm/sii.py", ["aasm.sii.v1", "authority_reward", "NEVER", "direct_truth_promotion", "self_verification"])

    require(root / "src/aasm/optimization.py", ["aasm.optimization.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "NATIVE_SOLVER_PROVIDER"])
    require(root / "src/aasm/_runtime_v44_optimization.py", ["commit_optimization_result", "optimization_reuse_request", "result_authority", "EVIDENCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", [
        "aasm.optimization.convex.v1",
        "AASM_OWNED",
        "EXISTING_AASM_RESOURCE_WORKER_LEASE",
        "EVIDENCE_ONLY",
        "DIAGONAL_ONLY_V0_45",
        "NORM2_VARIABLE_VECTOR_LE_CONSTANT_RADIUS",
        "direct_native_v44_paths_preserved",
    ])
    require(root / "src/aasm/_runtime_v45_convex.py", [
        "_validate_convex_lease",
        "convex result lease expired before result commit",
        "convex result lease was superseded by a newer attempt",
        "convex result implementation does not match admitted provider",
        "result_authority",
        "EVIDENCE_ONLY",
        "convex_reuse_request",
    ])
    require(root / "src/aasm/pulp_adapter.py", [
        "aasm.adapter.pulp.v1",
        "TRANSLATION_ONLY",
        '"solver_execution": "NEVER"',
        "REJECT_NOT_APPROXIMATE",
        "AASM_NATIVE_PORTFOLIO",
    ])

    print("v0.45 formal contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
