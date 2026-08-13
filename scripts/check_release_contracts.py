from __future__ import annotations
from pathlib import Path
import tomllib

def require(path: Path,tokens:list[str])->None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")

def main()->int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.35.0": raise SystemExit(f"unexpected release version: {version}")
    require(root/"src/aasm/__init__.py",['__version__ = "0.35.0"','"contract_version": "0.11.0"','SEMANTIC_PROBLEM_CONTRACT_ID'])
    require(root/"src/aasm/semantic_result.py",['DOMAIN_CONTRACT_ID = "aasm.domain.v1"','PROBLEM_CONTRACT_ID = "aasm.problem.v1"','class DomainPackage','class ProblemDefinition','class ProblemModel','class ProblemInstance','def build_problem_instance','def validate_problem_instance'])
    require(root/"src/aasm/runtime_v32.py",['def admit_semantic_problem','def semantic_problem_report','def semantic_domain_report','EvidenceRecord'])
    require(root/"src/aasm/cli_v32.py",['semantic-problem-contract','problem-admit','"problem"','"domain"'])
    require(root/"README.md",['Current release — v0.35.0','Semantic Problem Model Foundations','v0.36.0 — Semantic Compiler SDK'])
    require(root/"ROADMAP.md",['v0.35.0 — Semantic Problem Model Foundations','Current — implemented','v0.36.0 — Semantic Compiler SDK'])
    require(root/"docs/CURRENT_RELEASE.md",['AASM v0.35.0','aasm.semantic.problem.v1 / 0.1.0'])
    print("v0.35 semantic problem model, admission, and release contracts: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
