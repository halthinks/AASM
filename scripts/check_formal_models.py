from __future__ import annotations
from pathlib import Path
import tomllib

def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8"); missing = [t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing formal-contract tokens {missing}")

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle: version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.33.0": raise SystemExit(f"unexpected formal release version: {version}")
    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic", "FairnessProgress"])
    require(root / "formal/AASMScopeHierarchy.tla", ["RootAuthorityRetained", "ScopedRestartPreservesParentsAndSiblings"])
    require(root / "formal/AASMTraceConformance.tla", ["NoDroppedPrefix", "UnknownExplicit"])
    require(root / "src/aasm/trace_conformance.py", ["def project_trace", "def semantic_trace_check", "def verify_provenance_export"])
    require(root / ".github/workflows/formal.yml", ["Verify every bounded TLA+ model", "Verify every bounded Promela model"])
    print("v0.33 inherited formal and signed provenance contracts: PASS"); return 0

if __name__ == "__main__": raise SystemExit(main())
