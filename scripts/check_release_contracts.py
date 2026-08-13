from __future__ import annotations
from pathlib import Path
import tomllib


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing release/readiness tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.39.0": raise SystemExit(f"unexpected release version: {version}")
    require(root / "src/aasm/__init__.py", ['__version__ = "0.39.0"', '"contract_version": "0.15.0"', "TYPED_PROTOCOL_CONTRACT_ID", "CAPABILITY_ABI_CONTRACT_ID", "FORMAL_STATEMENT_CONTRACT_ID", "FORMAL_VERIFICATION_CONTRACT_ID"])
    require(root / "src/aasm/domain_adapters.py", ['SEMANTIC_SOURCE_CONTRACT_ID = "aasm.semantic.source.v1"', 'SEMANTIC_COMPILER_CONTRACT_ID = "aasm.semantic.compiler.v1"', "class DomainCompiler", "class InstanceCompiler", "def compile_and_admit", "PROPOSAL_ONLY", "AASM_EVENT_REDUCER_ONLY"])
    require(root / "src/aasm/reasoning.py", ['REASONING_ARTIFACT_CONTRACT_ID = "aasm.reasoning.artifact.v1"', 'EPISTEMIC_ADMISSION_CONTRACT_ID = "aasm.reasoning.admission.v1"', 'REASONING_COMMIT_CONTRACT_ID = "aasm.reasoning.commit.v1"', "RESERVED_FOR_V0.38"])
    require(root / "src/aasm/semantic_dependencies.py", ['SEMANTIC_DEPENDENCY_CONTRACT_ID = "aasm.semantic.dependencies.v1"', 'TRUTH_MAINTENANCE_CONTRACT_ID = "aasm.truth.maintenance.v1"', '"truth_change_policy": "AFFECTED_DESCENDANTS_ONLY"', '"reactive_policy": "DERIVE_OBLIGATION_NEVER_EXECUTE_HANDLER"'])
    require(root / "src/aasm/typed_protocol.py", ['TYPED_PROTOCOL_CONTRACT_ID = "aasm.typed.protocol.v1"', 'CAPABILITY_ABI_CONTRACT_ID = "aasm.capability.abi.v1"', 'FORMAL_STATEMENT_CONTRACT_ID = "aasm.formal.statement.v1"', 'FORMAL_VERIFICATION_CONTRACT_ID = "aasm.formal.verification.v1"', "class TypedEventSchema", "class ScopedLegalTransition", "class PatternMachine", "class CapabilityContract", "class CapabilityProvider"])
    require(root / "src/aasm/formal_models.py", ["class FormalStatement", "class FormalVerificationRequest", "class FormalVerificationResult", "ASSUMPTIONS_AND_NEGATED_CONJECTURE", "EVIDENCE_ONLY", "NOT_TRUTH", "NOT_A_REFUTATION", "def typed_protocol_contract", "def capability_abi_contract", "def formal_verification_contract"])
    require(root / "src/aasm/formal_workers.py", ["class ExecutableFormalWorker", "def aggregate_formal_results"])
    require(root / "src/aasm/formal_conformance.py", ["def run_typed_capability_conformance"])
    require(root / "src/aasm/typed_capabilities.py", ["from .typed_protocol import", "from .formal_models import", "from .formal_workers import", "from .formal_conformance import"])
    require(root / "src/aasm/_runtime_v39_typed.py", ["def admit_typed_pattern", "def propose_typed_transition", "def authorize_typed_transition", "unknown typed pattern scope", "self._begin_calculus", "self.add_evidence"])
    require(root / "src/aasm/_runtime_v39_capability_abi.py", ["def _validate_provider_contract", "def register_capability_contract", "def register_capability_provider", "def register_formal_provider_runtime", "existing worker is bound to a different resource", "WorkerRecord"])
    require(root / "src/aasm/_runtime_v39_formal_request.py", ["def propose_formal_statement", "def request_formal_verification", "TaskDemand", "_validate_formal_lease", "formal_verification_result"])
    require(root / "src/aasm/_runtime_v39_formal_result.py", ["def commit_formal_verification_result", "record_verification", "completed formal lease cannot commit a new result", "TRUSTED_KERNEL strength requires", "canonical status mismatch", "self.add_evidence", "EVIDENCE_ONLY"])
    require(root / "src/aasm/_runtime_v39_capabilities.py", ["class TypedCapabilityRuntimeMixin", "FormalResultRuntimeMixin", "FormalRequestRuntimeMixin", "CapabilityABIRuntimeMixin", "TypedProtocolRuntimeMixin"])
    require(root / "src/aasm/runtime_v39.py", ["TypedCapabilityRuntimeMixin", "V38Engine", "typed-transitions", "formal-verification", "formal-statements"])
    require(root / "src/aasm/cli_v39.py", ["typed-protocol-contract", "capability-abi-contract", "formal-verification-contract", "typed-capability-conformance", "typed-pattern-add", "typed-transition-propose", "typed-transition-authorize", "capability-add", "capability-provider-add", "formal-blueprint", "formal-provider-runtime", "formalize", "formal-request", "formal-report", "formal-result"])
    require(root / "README.md", ["Current release — v0.39.0", "Typed Protocol, Capability ABI, and Formal Verification Workers", "v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection"])
    require(root / "ROADMAP.md", ["v0.39.0 — Typed Protocol, Capability ABI, and Formal Verification Workers", "Current — implemented", "v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.39.0", "aasm.typed.protocol.v1", "aasm.capability.abi.v1", "aasm.formal.statement.v1", "aasm.formal.verification.v1"])
    require(root / "docs/TYPED_CAPABILITIES_FORMAL_VERIFICATION.md", ["formalization", "Vampire", "Z3", "cvc5", "Lean 4", "ASSUMPTIONS_AND_NEGATED_CONJECTURE", "NOT_A_REFUTATION", "TaskLease"])
    require(root / "CHANGELOG.md", ["## [0.39.0]", "## [0.38.0]", "## [0.37.0]", "## [0.36.0]", "## [0.35.0]"])
    for schema in ("typed-event-schema.schema.json", "pattern-machine.schema.json", "capability-contract.schema.json", "formal-statement.schema.json", "formal-verification-request.schema.json", "formal-verification-result.schema.json", "semantic-dependency.schema.json", "reasoning-artifact.schema.json"):
        require(root / "schemas" / schema, ['"$schema"', "2020-12"])
    print("v0.39 typed protocol, capability ABI, formal verification, documentation, and release contracts: PASS")
    return 0


if __name__ == "__main__": raise SystemExit(main())
