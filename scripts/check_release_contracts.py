from __future__ import annotations
from pathlib import Path
import tomllib

def require(path:Path,tokens:list[str])->None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")

def main()->int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.36.0": raise SystemExit(f"unexpected release version: {version}")
    require(root/"src/aasm/__init__.py",['__version__ = "0.36.0"','"contract_version": "0.12.0"','SEMANTIC_COMPILER_CONTRACT_ID'])
    require(root/"src/aasm/domain_adapters.py",['SEMANTIC_SOURCE_CONTRACT_ID = "aasm.semantic.source.v1"','SEMANTIC_COMPILER_CONTRACT_ID = "aasm.semantic.compiler.v1"','class DomainCompiler','class InstanceCompiler','class CompileResult','class ReferenceSemanticCompiler','def compile_semantic_source','def compile_and_admit','def run_semantic_compiler_conformance','PROPOSAL_ONLY','AASM_EVENT_REDUCER_ONLY'])
    require(root/"src/aasm/runtime_v32.py",['def compile_and_admit_semantic','def semantic_compiler_report'])
    require(root/"src/aasm/cli_v32.py",['semantic-compiler-contract','semantic-compile','semantic-compiler-conformance','semantic-compile-admit','problem-check'])
    require(root/"README.md",['Current release — v0.36.0','Semantic Compiler SDK','v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph'])
    require(root/"ROADMAP.md",['v0.36.0 — Semantic Compiler SDK','Current — implemented','v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph'])
    require(root/"docs/CURRENT_RELEASE.md",['AASM v0.36.0','aasm.semantic.compiler.v1 / 0.1.0'])
    require(root/"CHANGELOG.md",['## [0.36.0]','## [0.35.0]','## [0.34.0]','## [0.33.0]'])
    print("v0.36 semantic compiler, conformance, documentation, and release contracts: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
