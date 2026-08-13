from __future__ import annotations
from pathlib import Path
import tomllib

def require(path:Path,tokens:list[str])->None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing formal-contract tokens {missing}")

def main()->int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.36.0": raise SystemExit(f"unexpected formal release version: {version}")
    require(root/"formal/AASMCalculus.tla",["HardRequiresCertificate","CandidateActivationIsAtomic"])
    require(root/"formal/AASMScopeHierarchy.tla",["RootAuthorityRetained","ScopedRestartPreservesParentsAndSiblings"])
    require(root/"formal/AASMTraceConformance.tla",["NoDroppedPrefix","UnknownExplicit","InvalidSourceNeverAdmitted","CandidateRequiresValidSource","AdmissionRequiresEvidence"])
    require(root/"formal/aasm_trace_conformance.pml",["source_valid","candidate_ready","admission_evidence","durable_admitted"])
    require(root/"src/aasm/domain_adapters.py",['COMPILER_STAGES','PROPOSAL_ONLY','AASM_EVENT_REDUCER_ONLY','def compile_and_admit'])
    require(root/"src/aasm/runtime_v32.py",['EvidenceRecord','self.add_evidence','def compile_and_admit_semantic'])
    require(root/".github/workflows/formal.yml",["Verify every bounded TLA+ model","Verify every bounded Promela model"])
    print("v0.36 inherited formal and semantic compiler admission contracts: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
