from __future__ import annotations
from pathlib import Path
import tomllib

def require(path: Path,tokens:list[str])->None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing formal-contract tokens {missing}")

def main()->int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.34.0": raise SystemExit(f"unexpected formal release version: {version}")
    require(root/"formal/AASMCalculus.tla",["HardRequiresCertificate","CandidateActivationIsAtomic"])
    require(root/"formal/AASMScopeHierarchy.tla",["RootAuthorityRetained","ScopedRestartPreservesParentsAndSiblings"])
    require(root/"formal/AASMTraceConformance.tla",["NoDroppedPrefix","UnknownExplicit"])
    require(root/"src/aasm/operator_runbooks.py",["ONE_VALID_AUTHORITY_OR_EXPLICIT_RECONCILIATION","def certify_distributed_recovery"])
    require(root/".github/workflows/formal.yml",["Verify every bounded TLA+ model","Verify every bounded Promela model"])
    print("v0.34 inherited formal and distributed recovery contracts: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
