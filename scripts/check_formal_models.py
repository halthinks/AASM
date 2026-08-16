from pathlib import Path
import tomllib


def require(path, tokens):
    text = Path(path).read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.56.1":
        raise SystemExit(f"unexpected formal release version: {version}")

    # Core deterministic calculus and truth-maintenance models.
    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMSemanticTruthMaintenance.tla", ["AffectedDescendantsOnly", "UnrelatedSiblingPreserved"])
    require(root / "formal/AASMTypedCapabilities.tla", ["SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/AASMHierarchicalMemory.tla", ["StaleSemanticMemoryExcluded", "DerivedIndexCannotChangeMemoryIdentity"])
    require(root / "formal/AASMReusePlane.tla", ["SkipRequiresCertificate", "CertificateRequiresValidation", "CacheDeletionDoesNotDefineTruth"])
    require(root / "formal/AASMOptimizationPortfolio.tla", ["ResultRequiresLease", "ResultIsEvidence", "SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/aasm_optimization_portfolio.pml", ["task_leased", "result_evidence", "policy_acted", "truth_authorized"])

    require(root / "formal/AASMGovernedSII.tla", [
        "MeasurementRequiresBoundPrincipal", "LeaseRequiresActivePolicy", "ResourceAuthorityNeverEscalates",
        "SpendNeverExceedsLease", "RequiredVerificationNeverReduced", "SIINeverPromotesTruth",
        "SIINeverMutatesCanonicalState", "SIINeverSelfVerifies",
    ])
    require(root / "formal/aasm_governed_sii.pml", [
        "proposer_bound", "meter_bound", "policy_active", "budget_limit", "required_verification_enabled",
        "truth_promoted_by_sii", "state_mutated_by_sii", "self_verified_by_sii",
    ])
    require(root / "formal/AASMCrossRunKnowledge.tla", [
        "ForeignAuthorityNeverInherited", "AdmissionRequiredBeforeMaterialization", "AdmissionRequiredBeforeReuse",
        "RevocationBlocksReuse", "RevocationInvalidatesMaterializedMemory", "PrivateKnowledgeNeverLeaksAcrossPrincipal",
        "ReputationNeverGrantsAuthority", "ReputationNeverGrantsResourceEntitlement",
    ])
    require(root / "formal/aasm_cross_run_knowledge.pml", [
        "foreign_authority_inherited", "admission_validated", "admission_authorized", "materialized_active",
        "reuse_enabled", "source_revoked", "privacy_compatible", "reputation_granted_authority", "reputation_granted_resources",
    ])
    require(root / "formal/AASMSolutionPools.tla", [
        "CompleteImpliesExhausted", "CompleteImpliesIndependentChecker", "CompleteImpliesPassingChecker",
        "CompleteImpliesDurableCursor", "PartialModeNeverClaimsComplete", "CompletenessNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solution_pools.pml", [
        "cursor_durable", "solution_count", "exclusion_count", "exhausted", "checker_independent", "checker_passed", "complete", "truth_authorized",
    ])
    require(root / "formal/AASMSolverProofClaims.tla", [
        "ProofCertifiedImpliesIndependentChecker", "ProofCertifiedImpliesExactBinding", "ProofCertifiedImpliesPassingCheck",
        "SolverClaimNeverSelfCertifies", "FailedProofNeverCertifies", "UnsupportedProofNeverCertifies", "ProofCertificateNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solver_proof_claims.pml", [
        "checker_independent", "exact_binding", "proof_passed", "proof_failed", "proof_unsupported", "proof_certified", "truth_authorized",
    ])
    require(root / "src/aasm/solution_pools.py", [
        'SOLUTION_POOL_CONTRACT_ID = "aasm.optimization.solution-pool.v1"',
        'ENUMERATION_CONTRACT_ID = "aasm.optimization.enumeration.v1"',
        '"complete_requires_independent_exhaustion_certificate": True',
        '"bounded_or_native_pool_implies_completeness": False',
        '"result_authority": "EVIDENCE_ONLY"', "certify_complete_finite_enumeration", "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING",
    ])

    print("formal source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
