from pathlib import Path
import tomllib

def require(path,tokens):
    text=Path(path).read_text(); missing=[x for x in tokens if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")
def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'pyproject.toml').open('rb') as f: version=str(tomllib.load(f)['project']['version'])
    if version!='0.40.0': raise SystemExit(f'unexpected release version: {version}')
    require(root/'src/aasm/__init__.py',['__version__ = "0.40.0"','"contract_version": "0.16.0"','HIERARCHICAL_MEMORY_CONTRACT_ID'])
    require(root/'src/aasm/_public_v39.py',['__version__ = "0.39.0"','"contract_version": "0.15.0"'])
    require(root/'src/aasm/hierarchical_memory.py',['aasm.memory.hierarchical.v1','DECISION_TO_OBLIGATION_TO_EVIDENCE','DERIVED_INDEX_ONLY','TOMBSTONE_NOT_HISTORY_DELETION','class MemoryObject','class ContextProjectionRequest'])
    require(root/'src/aasm/_runtime_v40_memory.py',['def propose_memory_operation','def authorize_memory_operation','def commit_memory_operation','def admit_memory_index','self.add_evidence'])
    require(root/'src/aasm/_runtime_v40_privacy.py',['privacy_principal_id','principal_id'])
    require(root/'src/aasm/cli_v40.py',['memory-propose','memory-authorize','memory-commit','context-project'])
    require(root/'README.md',['Current release — v0.40.0','Embeddings are derived indexes','v0.41 next'])
    require(root/'ROADMAP.md',['v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection','Current — implemented','v0.41.0 — Domain-Neutral Autonomous Solver Loop'])
    require(root/'docs/CURRENT_RELEASE.md',['AASM v0.40.0','aasm.memory.hierarchical.v1'])
    require(root/'CHANGELOG.md',['## [0.40.0]','## [0.39.0]','## [0.38.0]','## [0.37.0]','## [0.36.0]'])
    for name in ('hierarchical-memory.schema.json','memory-index-entry.schema.json','context-projection-request.schema.json'):
        require(root/'schemas'/name,['"$schema"','2020-12'])
    print('v0.40 release contracts: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
