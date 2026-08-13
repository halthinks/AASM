from pathlib import Path
import tomllib

def require(path,tokens):
    text=Path(path).read_text(); missing=[x for x in tokens if x not in text]
    if missing: raise SystemExit(f"{path}: missing {missing}")

def main():
    root=Path(__file__).resolve().parents[1]
    with (root/'pyproject.toml').open('rb') as f: version=str(tomllib.load(f)['project']['version'])
    if version!='0.41.0': raise SystemExit(f'unexpected release version: {version}')
    require(root/'src/aasm/public_v41.py',['__version__="0.41.0"','"contract_version":"0.17.0"'])
    require(root/'src/aasm/reuse_model.py',['aasm.reuse.v1','INDEX_AND_VALIDATE_ONLY','PERFORMANCE_ONLY','EXPLICIT_VALIDATOR_REQUIRED'])
    require(root/'src/aasm/reuse_validation.py',['subsumption_validator_required','non_idempotent_effect_never_reused'])
    require(root/'src/aasm/_runtime_v41_reuse_records.py',['def register_reuse_candidate','self.add_evidence'])
    require(root/'src/aasm/_runtime_v41_reuse_commit.py',['def commit_reuse_certificate','self.add_evidence'])
    require(root/'src/aasm/_runtime_v41_solver.py',['def solver_step','SKIP_EXECUTION','ROUTE_CAPABILITY'])
    require(root/'README.md',['Current release — v0.41.0','Deterministic Reuse Plane','Next release:','aasm.remote.v1 / 0.19.0'])
    require(root/'docs/CURRENT_RELEASE.md',['AASM v0.41.0','aasm.reuse.v1','aasm.solver.loop.v1'])
    require(root/'docs/REUSE_AND_SOLVER_LOOP.md',['ReuseCertificate','SUBSUMES','HotReuseIndex'])
    for name in ('reuse-request.schema.json','reuse-certificate.schema.json','solver-step.schema.json'):
        require(root/'schemas'/name,['"$schema"','2020-12'])
    print('v0.41 release contracts: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
