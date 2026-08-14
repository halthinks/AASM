from pathlib import Path
import tomllib

def require(path,tokens):
    text=Path(path).read_text(); missing=[x for x in tokens if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")

def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'pyproject.toml').open('rb') as f: version=str(tomllib.load(f)['project']['version'])
    if version!='0.42.0': raise SystemExit(f'unexpected formal release version: {version}')
    require(root/'formal/AASMCalculus.tla',['HardRequiresCertificate','CandidateActivationIsAtomic'])
    require(root/'formal/AASMSemanticTruthMaintenance.tla',['AffectedDescendantsOnly','UnrelatedSiblingPreserved'])
    require(root/'formal/AASMTypedCapabilities.tla',['SolverNeverDirectlyAuthorizesKnowledge'])
    require(root/'formal/AASMHierarchicalMemory.tla',['StaleSemanticMemoryExcluded','DerivedIndexCannotChangeMemoryIdentity'])
    require(root/'formal/AASMReusePlane.tla',['SkipRequiresCertificate','CertificateRequiresValidation','CacheDeletionDoesNotDefineTruth'])
    require(root/'formal/aasm_reuse_plane.pml',['source_valid','visible','env_valid','deps_valid','certified','skipped'])
    require(root/'src/aasm/reuse_model.py',['INDEX_AND_VALIDATE_ONLY','PERFORMANCE_ONLY','EXPLICIT_VALIDATOR_REQUIRED'])
    require(root/'src/aasm/reuse_validation.py',['non_idempotent_effect_never_reused','subsumption_validator_required','verification_strength_mismatch'])
    require(root/'src/aasm/reference_domains.py',['aasm.reference-domains.v1','REFERENCE_HARNESS_ONLY','kernel_changes'])
    print('v0.42 formal contracts: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
