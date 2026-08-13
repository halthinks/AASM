from __future__ import annotations
from pathlib import Path
import tomllib

def require(path: Path, tokens: list[str]) -> None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")

def main() -> int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.34.0": raise SystemExit(f"unexpected release version: {version}")
    require(root/"src/aasm/__init__.py", ['__version__ = "0.34.0"','"contract_version": "0.10.0"','RECOVERY_CONTRACT_ID'])
    require(root/"src/aasm/operator_runbooks.py", ['RECOVERY_CONTRACT_ID = "aasm.recovery.v1"','def certify_distributed_recovery','stale_completion_rejection','unknown_effect_reconciliation'])
    require(root/"src/aasm/cli_v32.py", ["recovery-certify"])
    require(root/"README.md", ["Current release — v0.34.0","Distributed Recovery Certification","v0.35.0 — Semantic Problem Model Foundations"])
    require(root/"ROADMAP.md", ["v0.34.0 — Distributed Recovery Certification","Current — implemented","v0.36.0 — Semantic Compiler SDK"])
    require(root/"docs/CURRENT_RELEASE.md", ["AASM v0.34.0","aasm.recovery.v1 / 0.1.0"])
    print("v0.34 distributed recovery, documentation, and release contracts: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
