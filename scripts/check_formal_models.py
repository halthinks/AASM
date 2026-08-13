from __future__ import annotations
from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8"); missing = [token for token in tokens if token not in text]
    if missing: raise SystemExit(f"{path}: missing formal-contract tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle: version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.39.0": raise SystemExit(f"unexpected formal release version: {version}")
    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMScopeHierarchy.tla", ["RootAuthorityRetained", "ScopedRestartPreservesParentsAndSiblings"])
    require(root / "formal/AASMTraceConformance.tla", ["NoDroppedPrefix", "UnknownExplicit", "InvalidSourceNeverAdmitted", "CandidateRequiresValidSource", "AdmissionRequiresEvidence"])
    require(root / "formal/aasm_trace_conformance.pml", ["source_valid", "candidate_ready", "admission_evidence", "durable_admitted"])
    require(root / "src/aasm/domain_adapters.py", ["COMPILER_STAGES", "PROPOSAL_ONLY", "AASM_EVENT_REDUCER_ONLY", "def compile_and_admit"])
    require(root / "src/aasm/reasoning.py", ['"self_verification": "REJECTED"', '"durability_boundary": "AASM_EVIDENCE_EVENT_REDUCER_ONLY"', '"dependency_truth_maintenance": "RESERVED_FOR_V0.38"', "def next_reasoning_state"])
    require(root / "formal/AASMSemanticTruthMaintenance.tla", ["CompletionRequiresPlan", "AffectedDescendantsOnly", "UnrelatedSiblingPreserved", "DecisionInvalidatedAfterApply", "ConsumedWorkReopensAfterApply", "ReactiveDerivationNeverExecutesHandler"])
    require(root / "src/aasm/_runtime_v38_dependencies.py", ['kind="truth_maintenance_plan"', 'kind="truth_maintenance_applied"', "def apply_truth_change", "def resume_truth_maintenance", '"handler_execution": "NONE"'])
    require(root / "formal/AASMTypedCapabilities.tla", ["ProposalRequiresAdmittedPattern", "ActiveTransitionRequiresGuardsAndAuthority", "SolverResultRequiresFormalizationAndLease", "SolverNeverDirectlyAuthorizesKnowledge"])
    require(root / "formal/aasm_typed_capabilities.pml", ["pattern_admitted", "event_valid", "transition_proposed", "guards_satisfied", "transition_authorized", "transition_active", "formalized", "lease_held", "solver_result", "epistemic_verified", "epistemic_authorized"])
    require(root / "src/aasm/formal_models.py", ['"direct_pattern_register": "REJECTED"', '"lease_boundary": "AASM_TASK_LEASE"', '"solver_authority": "EVIDENCE_ONLY"', '"solver_voting": "NOT_TRUTH"', '"lean_rejection": "NOT_A_REFUTATION"', "ASSUMPTIONS_AND_NEGATED_CONJECTURE"])
    require(root / "src/aasm/formal_workers.py", ["class ExecutableFormalWorker", "def aggregate_formal_results"])
    require(root / "src/aasm/_runtime_v39_typed.py", ["unknown typed pattern scope", "def admit_typed_pattern", "def authorize_typed_transition", "self._begin_calculus", "self.add_evidence"])
    require(root / "src/aasm/_runtime_v39_capability_abi.py", ["def _validate_provider_contract", "def register_formal_provider_runtime", "existing worker is bound to a different resource"])
    require(root / "src/aasm/_runtime_v39_formal_request.py", ["def request_formal_verification", "_validate_formal_lease", "TaskDemand"])
    require(root / "src/aasm/_runtime_v39_formal_result.py", ["def commit_formal_verification_result", "completed formal lease cannot commit a new result", "TRUSTED_KERNEL strength requires", "certificate-checked strength requires", "canonical status mismatch", "record_verification", "self.add_evidence", "EVIDENCE_ONLY"])
    require(root / ".github/workflows/formal.yml", ["Verify every bounded TLA+ model", "Verify every bounded Promela model"])
    print("v0.39 inherited formal plus typed capability and formal-verifier authority contracts: PASS")
    return 0


if __name__ == "__main__": raise SystemExit(main())
