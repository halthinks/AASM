from pathlib import Path
import tomllib

def require(path,tokens):
    text=Path(path).read_text(); missing=[x for x in tokens if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")
def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'pyproject.toml').open('rb') as f: version=str(tomllib.load(f)['project']['version'])
    if version!='0.40.0': raise SystemExit(f'unexpected formal release version: {version}')
    require(root/'formal/AASMCalculus.tla',['HardRequiresCertificate','CandidateActivationIsAtomic'])
    require(root/'formal/AASMSemanticTruthMaintenance.tla',['AffectedDescendantsOnly','UnrelatedSiblingPreserved'])
    require(root/'formal/AASMTypedCapabilities.tla',['SolverNeverDirectlyAuthorizesKnowledge'])
    require(root/'formal/AASMHierarchicalMemory.tla',['MemoryAdmissionRequiresDecisionObligationEvidence','StaleSemanticMemoryExcluded','TombstonePreservesHistory','DerivedIndexCannotChangeMemoryIdentity','PrivateProjectionRequiresPrincipal','ContextBudgetBounded'])
    require(root/'formal/aasm_hierarchical_memory.pml',['decision_proposed','obligation_open','memory_evidence','principal_match','used_budget'])
    require(root/'src/aasm/hierarchical_memory.py',['DECISION_TO_OBLIGATION_TO_EVIDENCE','REFERENCES_V37_ADMITTED_REASONING','DERIVED_INDEX_ONLY','TOMBSTONE_NOT_HISTORY_DELETION'])
    print('v0.40 formal contracts: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
