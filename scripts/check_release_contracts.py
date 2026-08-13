from __future__ import annotations
from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8"); missing = [token for token in tokens if token not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle: version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.38.0": raise SystemExit(f"unexpected release version: {version}")
    require(root / "src/aasm/__init__.py", ['__version__ = "0.38.0"', '"contract_version": "0.14.0"', "SEMANTIC_DEPENDENCY_CONTRACT_ID", "TRUTH_MAINTENANCE_CONTRACT_ID", "REACTIVE_OBLIGATION_CONTRACT_ID", "CAUSAL_DECISION_CONTRACT_ID"])
    require(root / "src/aasm/domain_adapters.py", ['SEMANTIC_SOURCE_CONTRACT_ID = "aasm.semantic.source.v1"', 'SEMANTIC_COMPILER_CONTRACT_ID = "aasm.semantic.compiler.v1"', "class DomainCompiler", "class InstanceCompiler", "class CompileResult", "class ReferenceSemanticCompiler", "def compile_semantic_source", "def compile_and_admit", "def run_semantic_compiler_conformance", "PROPOSAL_ONLY", "AASM_EVENT_REDUCER_ONLY"])
    require(root / "src/aasm/reasoning.py", ['REASONING_ARTIFACT_CONTRACT_ID = "aasm.reasoning.artifact.v1"', 'EPISTEMIC_ADMISSION_CONTRACT_ID = "aasm.reasoning.admission.v1"', 'REASONING_COMMIT_CONTRACT_ID = "aasm.reasoning.commit.v1"', "RESERVED_FOR_V0.38"])
    require(root / "src/aasm/semantic_dependencies.py", ['SEMANTIC_DEPENDENCY_CONTRACT_ID = "aasm.semantic.dependencies.v1"', 'TRUTH_MAINTENANCE_CONTRACT_ID = "aasm.truth.maintenance.v1"', 'REACTIVE_OBLIGATION_CONTRACT_ID = "aasm.reactive.obligation.v1"', 'CAUSAL_DECISION_CONTRACT_ID = "aasm.causal.decision.v1"', "class SemanticNodeRef", "class SemanticDependency", "class CausalDecisionRecord", "class ReactiveObligationRule", "class TruthMaintenancePlan", "def build_semantic_dependency_graph", "def dependency_impact_report", "def dependency_lineage_report", "def dependency_memory_signals", "def run_semantic_dependency_conformance", '"propagating_edge_policy": "DAG_REQUIRED"', '"truth_change_policy": "AFFECTED_DESCENDANTS_ONLY"', '"unrelated_sibling_policy": "PRESERVE"', '"reactive_policy": "DERIVE_OBLIGATION_NEVER_EXECUTE_HANDLER"'])
    require(root / "src/aasm/_runtime_v38_dependencies.py", ["def register_semantic_dependency", "def register_causal_decision", "def register_reactive_obligation_rule", "def derive_reactive_obligations", "def apply_truth_change", "def resume_truth_maintenance", 'kind="truth_maintenance_plan"', 'kind="truth_maintenance_applied"', '"handler_execution": "NONE"'])
    require(root / "src/aasm/runtime_v32.py", ["SemanticDependencyRuntimeMixin", "ReasoningRuntimeMixin", "semantic-dependencies", "truth-maintenance", "reactive-obligations", "semantic-memory-signals"])
    require(root / "src/aasm/cli_v38.py", ["semantic-dependency-contract", "semantic-dependency-conformance", "dependency-graph", "dependency-impact", "dependency-lineage", "dependency-add", "causal-decision-add", "reactive-rule-add", "reactive-derive", "reactive-obligations", "truth-maintain", "truth-resume", "truth-maintenance-report", "semantic-memory-signals"])
    require(root / "README.md", ["Current release — v0.38.0", "Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance", "v0.39.0 — Typed Event/Transition Protocol and Capability ABI"])
    require(root / "ROADMAP.md", ["v0.38.0 — Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance", "Current — implemented", "v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.38.0", "aasm.semantic.dependencies.v1", "aasm.truth.maintenance.v1", "aasm.reactive.obligation.v1", "aasm.causal.decision.v1"])
    require(root / "docs/SEMANTIC_TRUTH_MAINTENANCE.md", ["affected descendants", "unrelated siblings", "Reasoning Frontier", "handler"])
    require(root / "CHANGELOG.md", ["## [0.38.0]", "## [0.37.0]", "## [0.36.0]", "## [0.35.0]", "## [0.34.0]"])
    for schema in ("semantic-dependency.schema.json", "causal-decision.schema.json", "reactive-obligation-rule.schema.json", "truth-maintenance-plan.schema.json", "reasoning-artifact.schema.json"):
        require(root / "schemas" / schema, ['"$schema"', "2020-12"])
    print("v0.38 dependency graph, causal decisions, reactive truth maintenance, documentation, and release contracts: PASS"); return 0


if __name__ == "__main__": raise SystemExit(main())
