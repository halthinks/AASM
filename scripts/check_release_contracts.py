from __future__ import annotations
from pathlib import Path
import tomllib

def require(path:Path,tokens:list[str])->None:
    text=path.read_text(encoding="utf-8"); missing=[t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")

def main()->int:
    root=Path(__file__).resolve().parents[1]
    with (root/"pyproject.toml").open("rb") as h: version=str(tomllib.load(h)["project"]["version"])
    if version!="0.37.0": raise SystemExit(f"unexpected release version: {version}")
    require(root/"src/aasm/__init__.py",['__version__ = "0.37.0"','"contract_version": "0.13.0"','REASONING_ARTIFACT_CONTRACT_ID','EPISTEMIC_ADMISSION_CONTRACT_ID','REASONING_COMMIT_CONTRACT_ID'])
    require(root/"src/aasm/domain_adapters.py",['SEMANTIC_SOURCE_CONTRACT_ID = "aasm.semantic.source.v1"','SEMANTIC_COMPILER_CONTRACT_ID = "aasm.semantic.compiler.v1"','class DomainCompiler','class InstanceCompiler','class CompileResult','class ReferenceSemanticCompiler','def compile_semantic_source','def compile_and_admit','def run_semantic_compiler_conformance','PROPOSAL_ONLY','AASM_EVENT_REDUCER_ONLY'])
    require(root/"src/aasm/reasoning.py",['REASONING_ARTIFACT_CONTRACT_ID = "aasm.reasoning.artifact.v1"','EPISTEMIC_ADMISSION_CONTRACT_ID = "aasm.reasoning.admission.v1"','REASONING_COMMIT_CONTRACT_ID = "aasm.reasoning.commit.v1"','class ReasoningArtifact','class ReasoningTransition','class ReasoningCommit','def project_reasoning_evidence','def run_reasoning_conformance','RESERVED_FOR_V0.38'])
    require(root/"src/aasm/runtime_v32.py",['def compile_and_admit_semantic','def semantic_compiler_report','ReasoningRuntimeMixin','reasoning-artifacts'])
    require(root/"src/aasm/_runtime_v37_reasoning.py",['def propose_artifact','def record_verification','def authorize_artifact','def reasoning_commit','def reasoning_report','def reasoning_provenance'])
    require(root/"src/aasm/cli_v32.py",['semantic-compiler-contract','semantic-compile','semantic-compiler-conformance','semantic-compile-admit','problem-check'])
    require(root/"src/aasm/cli_v37.py",['reasoning-contract','reasoning-conformance','reasoning-commit','reasoning-provenance'])
    require(root/"README.md",['Current release — v0.37.0','Reasoning Artifacts and Epistemic Admission','v0.38.0 — Semantic Dependency Graph and Truth Maintenance'])
    require(root/"ROADMAP.md",['v0.37.0 — Reasoning Artifacts and Epistemic Admission','Current — implemented','v0.38.0 — Semantic Dependency Graph and Truth Maintenance'])
    require(root/"docs/CURRENT_RELEASE.md",['AASM v0.37.0','aasm.reasoning.artifact.v1','aasm.reasoning.admission.v1','aasm.reasoning.commit.v1'])
    require(root/"CHANGELOG.md",['## [0.37.0]','## [0.36.0]','## [0.35.0]','## [0.34.0]','## [0.33.0]'])
    for schema in ('reasoning-artifact.schema.json','reasoning-transition.schema.json','reasoning-commit.schema.json'):
        require(root/"schemas"/schema,['"$schema"','2020-12'])
    print("v0.37 reasoning artifacts, epistemic admission, conformance, documentation, and release contracts: PASS"); return 0

if __name__=="__main__": raise SystemExit(main())
