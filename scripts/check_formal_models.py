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
    if version != "0.48.1":
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

    # v0.48 independently models receiving-run authority, materialization,
    # certified reuse, revocation, privacy, and SII-reputation separation.
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
    require(root / "formal/AASMCrossRunKnowledge.cfg", [
        "ForeignAuthorityNeverInherited", "AdmissionRequiredBeforeMaterialization",
        "AdmissionRequiredBeforeReuse", "RevocationBlocksReuse",
        "RevocationInvalidatesMaterializedMemory", "PrivateKnowledgeNeverLeaksAcrossPrincipal",
        "ReputationNeverGrantsAuthority", "ReputationNeverGrantsResourceEntitlement",
    ])
    require(root / "formal/aasm_cross_run_knowledge.pml", [
        "foreign_authority_inherited", "admission_validated", "admission_authorized",
        "materialized_active", "reuse_enabled", "source_revoked", "privacy_compatible",
        "reputation_granted_authority", "reputation_granted_resources",
    ])

    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"',
        'CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION = "0.1.0"',
        'CROSS_RUN_ADMISSION_CONTRACT_ID = "aasm.knowledge.cross-run.admission.v1"',
        'CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID = "aasm.principal.cross-run-map.v1"',
        '"authority_transfer": "NEVER"',
        '"source_authority": "PROVENANCE_ONLY_NEVER_INHERITED"',
        '"semantic_materialization": "LOCAL_AUTHORIZED_REASONING_REQUIRED"',
        '"reuse": "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED"',
        '"sii_reputation": "ACCOUNTING_ONLY_NEVER_AUTHORITY_OR_RESOURCE_ENTITLEMENT"',
    ])
    require(root / "src/aasm/_runtime_v48_knowledge.py", [
        "propose_cross_run_admission", "authorize_cross_run_admission", "commit_cross_run_admission",
        "materialize_cross_run_knowledge", "register_cross_run_reuse_candidate",
        "map_cross_run_principal", "admit_cross_run_sii_reputation",
        "source_authority_inherited", "used_by_sii_resource_lease",
    ])
    require(root / "src/aasm/runtime_v48.py", [
        "CrossRunKnowledgeRuntimeMixin", "V47Engine", "cross_run_source_not_active",
        "propose_memory_forget", "source_principal_id", "does not match admitted stable principal mapping",
    ])
    require(root / "src/aasm/_runtime_v41_reuse_certify.py", [
        'candidate_metadata.get("cross_run")', "admission_validator_id", "admission_validator_version", '"authority_inherited": False',
    ])

    require(root / "src/aasm/reuse_model.py", ["INDEX_AND_VALIDATE_ONLY", "PERFORMANCE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED", "OPTIMIZATION_RESULT"])
    require(root / "src/aasm/reuse_validation.py", ["non_idempotent_effect_never_reused", "subsumption_validator_required", "verification_strength_mismatch"])
    require(root / "src/aasm/reference_domains.py", ["aasm.reference-domains.v1", "REFERENCE_HARNESS_ONLY", "kernel_changes"])

    # Preserve governed SII and all historical solver/authority paths.
    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "CERTIFICATION_HARNESS_ONLY", "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM", "INCONCLUSIVE"])
    require(root / "src/aasm/sii.py", ["aasm.sii.v1", "authority_reward", "NEVER", "direct_truth_promotion", "self_verification"])
    require(root / "src/aasm/certification_v47.py", ['CERTIFICATION_CONTRACT_VERSION = "0.2.0"', '"sii-preview": "sii-governance"', "mandatory-verification-not-reduced"])
    require(root / "src/aasm/sii_governance.py", ['SII_GOVERNED_CONTRACT_VERSION = "0.3.0"', 'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"', "REQUIRED_VERIFICATION_NEVER_REDUCED", '"authority_reward": "NEVER"'])
    require(root / "src/aasm/_runtime_v47_sii.py", ["request_sii_advanced_optimization", "request_sii_formal_verification", "policy-required verification must use the ordinary formal path"])

    require(root / "src/aasm/optimization.py", ["aasm.optimization.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "NATIVE_SOLVER_PROVIDER"])
    require(root / "src/aasm/_runtime_v44_optimization.py", ["commit_optimization_result", "optimization_reuse_request", "result_authority", "EVIDENCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "DIAGONAL_ONLY_V0_45"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/advanced_optimization.py", ["aasm.optimization.advanced.v1", "SEARCH_STATE_NEVER_PROMOTES_TRUTH", "EPHEMERAL_PERFORMANCE_ONLY", "unsat_core", "warm_start", "affine_soc"])
    require(root / "src/aasm/_runtime_v46_advanced.py", ["advanced result lease expired before result commit", "advanced result implementation does not match admitted provider", "EVIDENCE_ONLY"])

    print("v0.48.1 formal contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
