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
    if version != "0.54.0":
        raise SystemExit(f"unexpected formal release version: {version}")

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
        "proposer_bound", "meter_bound", "policy_active", "budget_limit", "budget_used",
        "required_verification_enabled", "truth_promoted_by_sii", "state_mutated_by_sii", "self_verified_by_sii",
    ])

    require(root / "formal/AASMCrossRunKnowledge.tla", [
        "ForeignAuthorityNeverInherited", "AdmissionRequiredBeforeMaterialization", "AdmissionRequiredBeforeReuse",
        "RevocationBlocksReuse", "RevocationInvalidatesMaterializedMemory", "PrivateKnowledgeNeverLeaksAcrossPrincipal",
        "ReputationNeverGrantsAuthority", "ReputationNeverGrantsResourceEntitlement",
    ])
    require(root / "formal/AASMCrossRunKnowledge.cfg", [
        "ForeignAuthorityNeverInherited", "AdmissionRequiredBeforeMaterialization", "AdmissionRequiredBeforeReuse",
        "RevocationBlocksReuse", "RevocationInvalidatesMaterializedMemory", "PrivateKnowledgeNeverLeaksAcrossPrincipal",
        "ReputationNeverGrantsAuthority", "ReputationNeverGrantsResourceEntitlement",
    ])
    require(root / "formal/aasm_cross_run_knowledge.pml", [
        "foreign_authority_inherited", "admission_validated", "admission_authorized",
        "materialized_active", "reuse_enabled", "source_revoked", "privacy_compatible",
        "reputation_granted_authority", "reputation_granted_resources",
    ])

    # v0.51 solution-pool assurance remains a required parent layer for v0.52+.
    require(root / "formal/AASMSolutionPools.tla", [
        "CompleteImpliesExhausted", "CompleteImpliesIndependentChecker",
        "CompleteImpliesPassingChecker", "CompleteImpliesDurableCursor",
        "CompleteImpliesExclusionPerSolution", "PartialModeNeverClaimsComplete",
        "CompletenessNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/AASMSolutionPools.cfg", [
        "CompleteImpliesExhausted", "CompleteImpliesIndependentChecker",
        "CompleteImpliesPassingChecker", "CompleteImpliesDurableCursor",
        "CompleteImpliesExclusionPerSolution", "PartialModeNeverClaimsComplete",
        "CompletenessNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solution_pools.pml", [
        "cursor_durable", "solution_count", "exclusion_count", "exhausted",
        "checker_independent", "checker_passed", "complete", "policy_acted", "truth_authorized",
    ])
    require(root / "src/aasm/solution_pools.py", [
        'SOLUTION_POOL_CONTRACT_ID = "aasm.optimization.solution-pool.v1"',
        'ENUMERATION_CONTRACT_ID = "aasm.optimization.enumeration.v1"',
        'SOLUTION_POOL_STABILITY = "EXPERIMENTAL_ENFORCED"',
        '"complete_requires_independent_exhaustion_certificate": True',
        '"bounded_or_native_pool_implies_completeness": False',
        '"result_authority": "EVIDENCE_ONLY"',
        '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
        "certify_complete_finite_enumeration", "enumerate_native_binary_backend",
        "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING",
    ])
    require(root / "src/aasm/runtime_v51.py", ["SolutionPoolRuntimeMixin", "V50Engine"])
    require(root / "src/aasm/_runtime_v51_pools.py", [
        "start_solution_pool", "admit_solution_to_pool", "advance_solution_pool",
        "enumerate_complete_solution_pool", "solution_pool_record_type", "EVIDENCE_ONLY",
    ])

    require(root / "formal/AASMSolverProofClaims.tla", [
        "ProofCertifiedImpliesIndependentChecker", "ProofCertifiedImpliesExactBinding",
        "ProofCertifiedImpliesPassingCheck", "SolverClaimNeverSelfCertifies",
        "FailedProofNeverCertifies", "UnsupportedProofNeverCertifies",
        "ProofCertificateNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/AASMSolverProofClaims.cfg", [
        "ProofCertifiedImpliesIndependentChecker", "ProofCertifiedImpliesExactBinding",
        "ProofCertifiedImpliesPassingCheck", "SolverClaimNeverSelfCertifies",
        "FailedProofNeverCertifies", "UnsupportedProofNeverCertifies",
        "ProofCertificateNeverDirectlyAuthorizesTruth",
    ])
    require(root / "formal/aasm_solver_proof_claims.pml", [
        "checker_independent", "exact_binding", "proof_passed", "proof_failed",
        "proof_unsupported", "proof_certified", "policy_acted", "truth_authorized",
    ])
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        'SOLVER_PROOF_CONTRACT_VERSION = "0.1.0"',
        'SOLVER_PROOF_STABILITY = "EXPERIMENTAL_ENFORCED"',
        '"solver_status_is_proof_grade": False',
        '"proof_certified_requires_independent_checker": True',
        '"certificate_authority": "EVIDENCE_ONLY"',
        '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
        "ProofUnsupportedError", "build_finite_domain_proof", "verify_finite_domain_proof",
        "independent of the solver provider", "UNSUPPORTED",
    ])
    require(root / "src/aasm/runtime_v50.py", ["ProofClaimRuntimeMixin", "V49Engine"])
    require(root / "src/aasm/_runtime_v50_proof.py", [
        "solver_proof_contract_report", "solver_proof_claim_report", "certify_optimization_claim",
        '"authority": "EVIDENCE_ONLY"', 'snapshot.evidence.get("records", [])',
    ])

    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        'SEMANTIC_SOLVER_RC_CONTRACT_VERSION = "0.1.0"',
        'SEMANTIC_SOLVER_RC_STABILITY = "RELEASE_CANDIDATE"',
        '"runtime_extension": "THIN_V48_COMPOSITION_NO_NEW_KERNEL"',
        '"cross_backend_rule": "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE"',
        '"native_solver_claim": "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS"',
        '"claim_policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"',
        "run_upgrade_compatibility", "run_cross_backend_overlap_certification", "run_rc_benchmarks",
    ])
    require(root / "src/aasm/runtime_v49.py", ["SemanticSolverRCRuntimeMixin", "V48Engine"])
    require(root / "src/aasm/_runtime_v49_rc.py", [
        "semantic_solver_rc_freeze_manifest", "semantic_solver_rc_upgrade_report",
        "semantic_solver_rc_cross_backend_report", "semantic_solver_rc_benchmark_report",
        "semantic_solver_rc_claim_audit", "semantic_solver_rc_certify",
    ])

    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"',
        '"authority_transfer": "NEVER"', '"source_authority": "PROVENANCE_ONLY_NEVER_INHERITED"',
        '"semantic_materialization": "LOCAL_AUTHORIZED_REASONING_REQUIRED"',
        '"reuse": "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED"',
        '"sii_reputation": "ACCOUNTING_ONLY_NEVER_AUTHORITY_OR_RESOURCE_ENTITLEMENT"',
    ])
    require(root / "src/aasm/runtime_v48.py", ["CrossRunKnowledgeRuntimeMixin", "V47Engine", "cross_run_source_not_active", "propose_memory_forget"])
    require(root / "src/aasm/_runtime_v41_reuse_certify.py", ["admission_validator_id", "admission_validator_version", '"authority_inherited": False'])

    require(root / "src/aasm/reuse_model.py", ["INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED", "OPTIMIZATION_RESULT"])
    require(root / "src/aasm/reuse_validation.py", ["non_idempotent_effect_never_reused", "subsumption_validator_required", "verification_strength_mismatch"])
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", "kernel_changes"])

    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "CERTIFICATION_HARNESS_ONLY", "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM", "INCONCLUSIVE"])
    require(root / "src/aasm/sii_governance.py", ['SII_GOVERNED_CONTRACT_VERSION = "0.3.0"', 'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"', "REQUIRED_VERIFICATION_NEVER_REDUCED", '"authority_reward": "NEVER"'])
    require(root / "src/aasm/_runtime_v47_sii.py", ["request_sii_advanced_optimization", "request_sii_formal_verification", "policy-required verification must use the ordinary formal path"])

    require(root / "src/aasm/optimization.py", ["aasm.optimization.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "NATIVE_SOLVER_PROVIDER"])
    require(root / "src/aasm/_runtime_v44_optimization.py", ["commit_optimization_result", "optimization_reuse_request", "result_authority", "EVIDENCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/advanced_optimization.py", ["aasm.optimization.advanced.v1", "SEARCH_STATE_NEVER_PROMOTES_TRUTH", "EPHEMERAL_PERFORMANCE_ONLY", "unsat_core", "warm_start", "affine_soc"])
    require(root / "src/aasm/_runtime_v46_advanced.py", ["advanced result lease expired before result commit", "advanced result implementation does not match admitted provider", "EVIDENCE_ONLY"])

    print("v0.54.0 formal contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
