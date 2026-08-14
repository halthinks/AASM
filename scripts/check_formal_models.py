from pathlib import Path
import tomllib

def require(path,tokens):
    text=Path(path).read_text(); missing=[x for x in tokens if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")

def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'pyproject.toml').open('rb') as f: version=str(tomllib.load(f)['project']['version'])
    if version!='0.44.0': raise SystemExit(f'unexpected formal release version: {version}')
    require(root/'formal/AASMCalculus.tla',['HardRequiresCertificate','CandidateActivationIsAtomic'])
    require(root/'formal/AASMSemanticTruthMaintenance.tla',['AffectedDescendantsOnly','UnrelatedSiblingPreserved'])
    require(root/'formal/AASMTypedCapabilities.tla',['SolverNeverDirectlyAuthorizesKnowledge'])
    require(root/'formal/AASMHierarchicalMemory.tla',['StaleSemanticMemoryExcluded','DerivedIndexCannotChangeMemoryIdentity'])
    require(root/'formal/AASMReusePlane.tla',['SkipRequiresCertificate','CertificateRequiresValidation','CacheDeletionDoesNotDefineTruth'])
    require(root/'formal/AASMOptimizationPortfolio.tla',['ResultRequiresLease','ResultIsEvidence','SolverNeverDirectlyAuthorizesKnowledge'])
    require(root/'formal/aasm_optimization_portfolio.pml',['task_leased','result_evidence','policy_acted','truth_authorized'])
    require(root/'src/aasm/reuse_model.py',['INDEX_AND_VALIDATE_ONLY','PERFORMANCE_ONLY','EXPLICIT_VALIDATOR_REQUIRED'])
    require(root/'src/aasm/reuse_validation.py',['non_idempotent_effect_never_reused','subsumption_validator_required','verification_strength_mismatch'])
    require(root/'src/aasm/reference_domains.py',['aasm.reference-domains.v1','REFERENCE_HARNESS_ONLY','kernel_changes'])
    require(root/'src/aasm/certification.py',['aasm.certification.v1','CERTIFICATION_HARNESS_ONLY','NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM','INCONCLUSIVE'])
    require(root/'src/aasm/sii.py',['aasm.sii.v1','authority_reward','NEVER','direct_truth_promotion','self_verification'])
    require(root/'src/aasm/optimization.py',['aasm.optimization.v1','EXISTING_AASM_RESOURCE_WORKER_LEASE','EVIDENCE_ONLY','NATIVE_SOLVER_PROVIDER'])
    require(root/'src/aasm/_runtime_v44_optimization.py',['commit_optimization_result','optimization_reuse_request','result_authority','EVIDENCE_ONLY'])
    print('v0.44 formal contracts: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
