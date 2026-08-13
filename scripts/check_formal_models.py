from __future__ import annotations
from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing formal-contract tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.37.0":
        raise SystemExit(f"unexpected formal release version: {version}")

    # Inherited calculus, scope, trace, compiler-admission, and provenance boundaries.
    require(root / "formal/AASMCalculus.tla", ["HardRequiresCertificate", "CandidateActivationIsAtomic"])
    require(root / "formal/AASMScopeHierarchy.tla", ["RootAuthorityRetained", "ScopedRestartPreservesParentsAndSiblings"])
    require(root / "formal/AASMTraceConformance.tla", ["NoDroppedPrefix", "UnknownExplicit", "InvalidSourceNeverAdmitted", "CandidateRequiresValidSource", "AdmissionRequiresEvidence"])
    require(root / "formal/aasm_trace_conformance.pml", ["source_valid", "candidate_ready", "admission_evidence", "durable_admitted"])
    require(root / "src/aasm/domain_adapters.py", ["COMPILER_STAGES", "PROPOSAL_ONLY", "AASM_EVENT_REDUCER_ONLY", "def compile_and_admit"])
    require(root / "src/aasm/runtime_v32.py", ["EvidenceRecord", "self.add_evidence", "def compile_and_admit_semantic", "ReasoningRuntimeMixin"])

    # v0.37 epistemic-admission invariants are executable source contracts over the
    # same Evidence/event/reducer boundary. Full dependency truth maintenance is v0.38.
    require(root / "src/aasm/reasoning.py", [
        'EPISTEMIC_ADMISSION_CONTRACT_ID = "aasm.reasoning.admission.v1"',
        'REASONING_COMMIT_CONTRACT_ID = "aasm.reasoning.commit.v1"',
        '"self_verification": "REJECTED"',
        '"durability_boundary": "AASM_EVIDENCE_EVENT_REDUCER_ONLY"',
        '"dependency_truth_maintenance": "RESERVED_FOR_V0.38"',
        "def next_reasoning_state",
        "def project_reasoning_evidence",
        "def run_reasoning_conformance",
    ])
    require(root / "src/aasm/_runtime_v37_reasoning.py", [
        "self-verification is not an admissible reasoning transition",
        "artifact authorization requires POLICY or CONTROLLER authority",
        'kind="reasoning_transition"',
        'kind="reasoning_commit"',
        "self.add_evidence",
    ])
    require(root / ".github/workflows/formal.yml", ["Verify every bounded TLA+ model", "Verify every bounded Promela model"])

    print("v0.37 inherited formal plus reasoning epistemic-admission contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
