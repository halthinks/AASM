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
    if version != "0.55.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    # Core deterministic calculus and truth-maintenance models.
    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMSemanticTruthMaintenance.tla", ["AffectedDescendantsOnly", "UnrelatedSiblingPreserved"])
    require(root / "formal/AASMTypedCapabilities.tla", ["SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/AASMHierarchicalMemory.tla", ["StaleSemanticMemoryExcluded", "DerivedIndexCannotChangeMemoryIdentity"])
    require(root / "formal/AASMReusePlane.tla", ["SkipRequiresCertificate", "CertificateRequiresValidation", "CacheDeletionDoesNotDefineTruth"])
    require(root / "formal/AASMOptimizationPortfolio.tla", ["ResultRequiresLease", "ResultIsEvidence", "SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/aasm_optimization_portfolio.pml", ["task_leased", "result_evidence", "policy_acted", "truth_authorized"])

    # Governed SII cannot purchase authority or suppress required verification.
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
    require(root / "formal/aasm_governed_sii.pml", [
        "proposer_bound",
        "meter_bound",
        "policy_active",
        "budget_limit",
        "required_verification_enabled",
        "truth_promoted_by_sii",
        "state_mutated_by_sii",
        "self_verified_by_sii",
    ])

    # Cross-run knowledge carries provenance, never foreign authority.
    require(root / "formal/AASMCrossRunKnowledge.tla", [
        "ForeignAuthorityNeverInherited",
        "AdmissionRequiredBeforeMaterialization",
        "AdmissionRequiredBeforeReuse",
        "RevocationBlocksReuse",
        "RevocationInvalidatesMaterializedMemory",
        "PrivateKnowledgeNeverLeaksAcrossPrincipal",
        "ReputationNeverGrantsAuthority",
        "ReputationNeverGrantsResourceEntitlement",
    ])
    require(root / "formal/aasm_cross_run_knowledge.pml", [
        "foreign_authority_inherited",
        "admission_validated",
        "admission_authorized",
        "materialized_active",
        "reuse_enabled",
        "source_revoked",
        "privacy_compatible",
        "reputation_granted_authority",
        "reputation_granted_resources",
    ])

    # Complete enumeration and proof claims remain independently gated parent semantics.
    require(root / "formal/AASMSolutionPools.tla", [
        "CompleteImpliesExhausted",
        "CompleteImpliesIndependentChecker",
        "CompleteImpliesPassingChecker",
        "CompleteImpliesDurableCursor",
        "PartialModeNeverClaimsComplete",
        "CompletenessNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solution_pools.pml", [
        "cursor_durable",
        "solution_count",
        "exclusion_count",
        "exhausted",
        "checker_independent",
        "checker_passed",
        "complete",
        "truth_authorized",
    ])
    require(root / "formal/AASMSolverProofClaims.tla", [
        "ProofCertifiedImpliesIndependentChecker",
        "ProofCertifiedImpliesExactBinding",
        "ProofCertifiedImpliesPassingCheck",
        "SolverClaimNeverSelfCertifies",
        "FailedProofNeverCertifies",
        "UnsupportedProofNeverCertifies",
        "ProofCertificateNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solver_proof_claims.pml", [
        "checker_independent",
        "exact_binding",
        "proof_passed",
        "proof_failed",
        "proof_unsupported",
        "proof_certified",
        "truth_authorized",
    ])

    # Current implementation must still bind the formal abstractions to real runtime contracts.
    require(root / "src/aasm/solution_pools.py", [
        'SOLUTION_POOL_CONTRACT_ID = "aasm.optimization.solution-pool.v1"',
        'ENUMERATION_CONTRACT_ID = "aasm.optimization.enumeration.v1"',
        '"complete_requires_independent_exhaustion_certificate": True',
        '"bounded_or_native_pool_implies_completeness": False',
        '"result_authority": "EVIDENCE_ONLY"',
        "certify_complete_finite_enumeration",
        "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING",
    ])
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        '"solver_status_is_proof_grade": False',
        '"proof_certified_requires_independent_checker": True',
        '"certificate_authority": "EVIDENCE_ONLY"',
        "ProofUnsupportedError",
        "verify_finite_domain_proof",
        "UNSUPPORTED",
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        '"cross_backend_rule": "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE"',
        '"claim_policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"',
        "run_upgrade_compatibility",
        "run_cross_backend_overlap_certification",
        "run_rc_benchmarks",
    ])
    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"',
        '"authority_transfer": "NEVER"',
        '"source_authority": "PROVENANCE_ONLY_NEVER_INHERITED"',
        '"semantic_materialization": "LOCAL_AUTHORIZED_REASONING_REQUIRED"',
    ])
    require(root / "src/aasm/reuse_model.py", ["INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED", "OPTIMIZATION_RESULT"])
    require(root / "src/aasm/reuse_validation.py", ["non_idempotent_effect_never_reused", "subsumption_validator_required", "verification_strength_mismatch"])
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", "kernel_changes"])
    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "CERTIFICATION_HARNESS_ONLY", "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM", "INCONCLUSIVE"])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"',
        'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"',
        "REQUIRED_VERIFICATION_NEVER_REDUCED",
        '"authority_reward": "NEVER"',
    ])

    # Optimization/modeling adapters preserve the established execution/evidence boundary.
    require(root / "src/aasm/optimization.py", ["aasm.optimization.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "NATIVE_SOLVER_PROVIDER"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/advanced_optimization.py", ["aasm.optimization.advanced.v1", "SEARCH_STATE_NEVER_PROMOTES_TRUTH", "EPHEMERAL_PERFORMANCE_ONLY", "unsat_core", "warm_start", "affine_soc"])

    # v0.55 adds semantic/formulation/engineering contracts without claiming new formal proof coverage.
    require(root / "src/aasm/semantic_evolution.py", ["aasm.external.reference.v1", "aasm.problem.revision.v1", "aasm.problem.delta.v1"])
    require(root / "src/aasm/solver_formulation.py", [
        'SOLVER_FORMULATION_CONTRACT_ID = "aasm.solver.formulation.v1"',
        '"nontrivial_translation_policy": "NO_PASS_WITHOUT_AN_INDEPENDENT_CHECKER_FOR_THE_REQUESTED_FIDELITY"',
    ])
    require(root / "src/aasm/semantic_archive.py", [
        '"replay": "EXISTING_AASM_REDUCER_OVER_ARCHIVED_EVENTS"',
        '"replay_uses_persisted_snapshot": False',
    ])

    print("v0.55.0 formal contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
