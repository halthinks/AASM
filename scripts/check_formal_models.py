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
    if version != "0.47.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMSemanticTruthMaintenance.tla", ["AffectedDescendantsOnly", "UnrelatedSiblingPreserved"])
    require(root / "formal/AASMTypedCapabilities.tla", ["SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/AASMHierarchicalMemory.tla", ["StaleSemanticMemoryExcluded", "DerivedIndexCannotChangeMemoryIdentity"])
    require(root / "formal/AASMReusePlane.tla", ["SkipRequiresCertificate", "CertificateRequiresValidation", "CacheDeletionDoesNotDefineTruth"])
    require(root / "formal/AASMOptimizationPortfolio.tla", ["ResultRequiresLease", "ResultIsEvidence", "SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/aasm_optimization_portfolio.pml", ["task_leased", "result_evidence", "policy_acted", "truth_authorized"])

    # v0.47 independently models the SII graduation boundaries rather than
    # relying only on source assertions around the runtime implementation.
    require(root / "formal/AASMGovernedSII.tla", [
        "MeasurementRequiresBoundPrincipal",
        "LeaseRequiresActivePolicy",
        "ResourceAuthorityNeverEscalates",
        "SpendNeverExceedsLease",
        "RequiredVerificationNeverReduced",
        "SIINeverPromotesTruth",
        "SIINeverMutatesCanonicalState",
        "SIINeverSelfVerifies",
    ])
    require(root / "formal/AASMGovernedSII.cfg", [
        "MeasurementRequiresBoundPrincipal",
        "ResourceAuthorityNeverEscalates",
        "SpendNeverExceedsLease",
        "RequiredVerificationNeverReduced",
    ])
    require(root / "formal/aasm_governed_sii.pml", [
        "proposer_bound", "meter_bound", "policy_active", "budget_limit", "budget_used",
        "required_verification_enabled", "truth_promoted_by_sii", "state_mutated_by_sii", "self_verified_by_sii",
    ])

    require(root / "src/aasm/reuse_model.py", ["INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED", "OPTIMIZATION_RESULT"])
    require(root / "src/aasm/reuse_validation.py", ["non_idempotent_effect_never_reused", "subsumption_validator_required", "verification_strength_mismatch"])
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", "kernel_changes"])

    # Preserve the historical v0.43 preview as a compatibility substrate, while
    # current certification/SII authority is defined by the versioned facades.
    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "CERTIFICATION_HARNESS_ONLY", "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM", "INCONCLUSIVE"])
    require(root / "src/aasm/sii.py", ["aasm.sii.v1", "authority_reward", "NEVER", "direct_truth_promotion", "self_verification"])
    require(root / "src/aasm/certification_v47.py", [
        'CERTIFICATION_CONTRACT_VERSION = "0.2.0"',
        '"sii-preview": "sii-governance"',
        "measurement-principal-authority-binding",
        "resource-lease-native-solver-enforcement",
        "mandatory-verification-not-reduced",
    ])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"',
        'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"',
        "DURABLE_POLICY_OR_CONTROLLER_ADMISSION",
        "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING",
        "VERSIONED_DURABLE_POLICY",
        "EXISTING_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_SOLVER_PATHS",
        "REQUIRED_VERIFICATION_NEVER_REDUCED",
        '"authority_reward": "NEVER"',
        '"self_verification": "REJECTED"',
        '"direct_state_mutation": "REJECTED"',
    ])
    require(root / "src/aasm/_runtime_v47_sii.py", [
        "request_sii_advanced_optimization",
        "request_sii_formal_verification",
        "SII max_parallel_candidates budget exhausted",
        "policy-required verification must use the ordinary formal path",
        '"authority_reward": "NEVER"',
    ])

    # All previously released solver/authority paths remain first class.
    require(root / "src/aasm/optimization.py", ["aasm.optimization.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "NATIVE_SOLVER_PROVIDER"])
    require(root / "src/aasm/_runtime_v44_optimization.py", ["commit_optimization_result", "optimization_reuse_request", "result_authority", "EVIDENCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "DIAGONAL_ONLY_V0_45"])
    require(root / "src/aasm/_runtime_v45_convex.py", ["convex result lease expired before result commit", "convex result lease was superseded by a newer attempt", "result_authority", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"', "REJECT_NOT_APPROXIMATE"])
    require(root / "src/aasm/advanced_optimization.py", [
        "aasm.optimization.advanced.v1",
        "EXISTING_AASM_RESOURCE_WORKER_LEASE",
        "EVIDENCE_ONLY",
        "SEARCH_STATE_NEVER_PROMOTES_TRUTH",
        "EPHEMERAL_PERFORMANCE_ONLY",
        "unsat_core",
        "warm_start",
        "affine_soc",
    ])
    require(root / "src/aasm/_runtime_v46_advanced.py", [
        "advanced result lease expired before result commit",
        "advanced result lease was superseded by a newer attempt",
        "advanced result implementation does not match admitted provider",
        "result_authority",
        "EVIDENCE_ONLY",
        "advanced_optimization_reuse_request",
    ])

    print("v0.47 formal contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
