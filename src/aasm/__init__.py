from copy import deepcopy as _deepcopy

from . import _public_v31 as _v31
from ._public_v31 import *  # noqa: F401,F403
from .runtime_v32 import AASMEngine, default_profile_registry
from .trace_conformance import (
    TRACE_CONTRACT_ID, TRACE_CONTRACT_VERSION, SEMANTIC_TRACE_CONTRACT_ID, SEMANTIC_TRACE_CONTRACT_VERSION,
    PROVENANCE_CONTRACT_ID, PROVENANCE_CONTRACT_VERSION, TraceIssue, trace_contract, project_trace,
    semantic_trace_check, build_trace_corpus, provenance_contract, export_provenance,
    verify_provenance_export, create_selective_provenance_export,
)
from .operator_runbooks import (
    RECOVERY_CONTRACT_ID, RECOVERY_CONTRACT_VERSION, RECOVERY_SCENARIOS,
    distributed_recovery_contract, certify_distributed_recovery,
)
from .semantic_result import (
    DOMAIN_CONTRACT_ID, DOMAIN_CONTRACT_VERSION, PROBLEM_CONTRACT_ID, PROBLEM_CONTRACT_VERSION,
    SEMANTIC_PROBLEM_CONTRACT_ID, SEMANTIC_PROBLEM_CONTRACT_VERSION, COMPILE_STATUSES,
    Entity, Predicate, Objective, Operator, Observer, Verifier, DomainPackage, ProblemDefinition,
    ProblemModel, ProblemInstance, canonical_semantic_json, semantic_fingerprint,
    semantic_problem_contract, validate_problem_model, build_problem_instance,
    validate_problem_instance, semantic_problem_document, semantic_problem_from_document,
)
from .domain_adapters import (
    SEMANTIC_SOURCE_CONTRACT_ID, SEMANTIC_SOURCE_CONTRACT_VERSION,
    SEMANTIC_COMPILER_CONTRACT_ID, SEMANTIC_COMPILER_CONTRACT_VERSION, COMPILER_STAGES,
    CompilerDeclaration, EnvironmentSnapshot, RawProblemInput, CompilerDiagnostic, CompileResult,
    DomainCompiler, InstanceCompiler, ReferenceSemanticCompiler, CompilationCache,
    semantic_compiler_contract, compile_semantic_source, compile_and_admit,
    reference_semantic_source, run_semantic_compiler_conformance,
)
from .reasoning import (
    REASONING_ARTIFACT_CONTRACT_ID, REASONING_ARTIFACT_CONTRACT_VERSION,
    EPISTEMIC_ADMISSION_CONTRACT_ID, EPISTEMIC_ADMISSION_CONTRACT_VERSION,
    REASONING_COMMIT_CONTRACT_ID, REASONING_COMMIT_CONTRACT_VERSION,
    REASONING_ARTIFACT_KINDS, REASONING_AUTHORITY_CLASSES, REASONING_STATES, REASONING_ACTIONS,
    ReasoningProducer, VerifierRequirement, ReasoningArtifact, Claim, Hypothesis, Lemma, Invariant,
    Counterexample, Definition, Assumption, Observation, Derivation, Refutation, ObjectiveResult,
    ReasoningTransition, ReasoningCommit, reasoning_contract, next_reasoning_state,
    project_reasoning_evidence, reasoning_artifact_document, reasoning_transition_document,
    reasoning_commit_document, run_reasoning_conformance,
)

__version__ = "0.37.0"
REMOTE_PROTOCOL_NAME = "aasm.remote.v1"
REMOTE_PROTOCOL_VERSION = "0.19.0"

from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__

_NEW_IMPORTS = [
    "TRACE_CONTRACT_ID", "TRACE_CONTRACT_VERSION", "SEMANTIC_TRACE_CONTRACT_ID", "SEMANTIC_TRACE_CONTRACT_VERSION",
    "PROVENANCE_CONTRACT_ID", "PROVENANCE_CONTRACT_VERSION", "TraceIssue", "trace_contract", "project_trace",
    "semantic_trace_check", "build_trace_corpus", "provenance_contract", "export_provenance",
    "verify_provenance_export", "create_selective_provenance_export", "RECOVERY_CONTRACT_ID",
    "RECOVERY_CONTRACT_VERSION", "RECOVERY_SCENARIOS", "distributed_recovery_contract", "certify_distributed_recovery",
    "DOMAIN_CONTRACT_ID", "DOMAIN_CONTRACT_VERSION", "PROBLEM_CONTRACT_ID", "PROBLEM_CONTRACT_VERSION",
    "SEMANTIC_PROBLEM_CONTRACT_ID", "SEMANTIC_PROBLEM_CONTRACT_VERSION", "COMPILE_STATUSES",
    "Entity", "Predicate", "Objective", "Operator", "Observer", "Verifier", "DomainPackage", "ProblemDefinition",
    "ProblemModel", "ProblemInstance", "canonical_semantic_json", "semantic_fingerprint", "semantic_problem_contract",
    "validate_problem_model", "build_problem_instance", "validate_problem_instance", "semantic_problem_document", "semantic_problem_from_document",
    "SEMANTIC_SOURCE_CONTRACT_ID", "SEMANTIC_SOURCE_CONTRACT_VERSION", "SEMANTIC_COMPILER_CONTRACT_ID",
    "SEMANTIC_COMPILER_CONTRACT_VERSION", "COMPILER_STAGES", "CompilerDeclaration", "EnvironmentSnapshot",
    "RawProblemInput", "CompilerDiagnostic", "CompileResult", "DomainCompiler", "InstanceCompiler",
    "ReferenceSemanticCompiler", "CompilationCache", "semantic_compiler_contract", "compile_semantic_source",
    "compile_and_admit", "reference_semantic_source", "run_semantic_compiler_conformance",
    "REASONING_ARTIFACT_CONTRACT_ID", "REASONING_ARTIFACT_CONTRACT_VERSION",
    "EPISTEMIC_ADMISSION_CONTRACT_ID", "EPISTEMIC_ADMISSION_CONTRACT_VERSION",
    "REASONING_COMMIT_CONTRACT_ID", "REASONING_COMMIT_CONTRACT_VERSION",
    "REASONING_ARTIFACT_KINDS", "REASONING_AUTHORITY_CLASSES", "REASONING_STATES", "REASONING_ACTIONS",
    "ReasoningProducer", "VerifierRequirement", "ReasoningArtifact", "Claim", "Hypothesis", "Lemma", "Invariant",
    "Counterexample", "Definition", "Assumption", "Observation", "Derivation", "Refutation", "ObjectiveResult",
    "ReasoningTransition", "ReasoningCommit", "reasoning_contract", "next_reasoning_state",
    "project_reasoning_evidence", "reasoning_artifact_document", "reasoning_transition_document",
    "reasoning_commit_document", "run_reasoning_conformance",
]
_NEW_METHODS = [
    "trace_projection", "semantic_trace_report", "provenance_export", "provenance_verify", "provenance_select",
    "admit_semantic_problem", "semantic_problem_report", "semantic_domain_report",
    "semantic_compiler_report", "compile_and_admit_semantic",
    "propose_artifact", "support_artifact", "contest_artifact", "request_verification",
    "record_verification", "authorize_artifact", "refute_artifact", "mark_stale", "reject_artifact",
    "reasoning_commit", "reasoning_report", "reasoning_provenance", "reasoning_contract_report",
]
_NEW_COMMANDS = [
    "trace-project", "trace-check", "provenance-export", "provenance-verify", "provenance-select", "recovery-certify",
    "semantic-problem-contract", "problem-admit", "problem", "domain", "semantic-compiler-contract",
    "semantic-compile", "semantic-compiler-conformance", "semantic-compile-admit", "compile", "problem-check",
    "reasoning-contract", "reasoning", "reasoning-artifact", "reasoning-provenance", "reasoning-commit",
    "reasoning-conformance",
]
_NEW_SURFACES = [
    "trace", "trace-semantic", "provenance", "problem", "semantic-problem", "domain", "semantic-domain",
    "compiler", "semantic-compiler", "reasoning", "reasoning-artifacts", "epistemic",
    "reasoning-contract", "epistemic-contract",
]

SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*_v31.SUPPORTED_PUBLIC_IMPORTS, *_NEW_IMPORTS]))
SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*_v31.SUPPORTED_ENGINE_METHODS, *_NEW_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*_v31.SUPPORTED_CLI_COMMANDS, *_NEW_COMMANDS]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*_v31.SUPPORTED_INSPECTION_SURFACES, *_NEW_SURFACES]))

PUBLIC_API_CONTRACT = _deepcopy(_v31.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.13.0", "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS, "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS, "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["trace_conformance"] = {
    "contract_id": TRACE_CONTRACT_ID, "contract_version": TRACE_CONTRACT_VERSION,
    "semantic_contract_id": SEMANTIC_TRACE_CONTRACT_ID, "semantic_contract_version": SEMANTIC_TRACE_CONTRACT_VERSION,
    "source": "AUTHORITATIVE_DURABLE_EVENT_HISTORY", "unknown_transition_policy": "UNSUPPORTED_EXPLICIT", "snapshot_only_input": "REJECTED",
}
PUBLIC_API_CONTRACT["provenance"] = provenance_contract()
PUBLIC_API_CONTRACT["distributed_recovery"] = distributed_recovery_contract()
PUBLIC_API_CONTRACT["semantic_problem"] = semantic_problem_contract()
PUBLIC_API_CONTRACT["semantic_compiler"] = semantic_compiler_contract()
PUBLIC_API_CONTRACT["reasoning"] = reasoning_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["golden_path"] = list(dict.fromkeys([
    *PUBLIC_API_CONTRACT.get("golden_path", []),
    "compile a normalized semantic source deterministically and admit only through the AASM event/reducer boundary",
    "propose reasoning artifacts, verify them independently, authorize them by policy, and commit only admitted knowledge",
]))


def public_api_contract() -> dict: return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    errors = []
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports: errors.append(f"missing public imports: {missing_imports}")
    if missing_methods: errors.append(f"missing AASMEngine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__: errors.append("runtime version mismatch")
    compiler = PUBLIC_API_CONTRACT.get("semantic_compiler") or {}
    if compiler.get("contract_id") != SEMANTIC_COMPILER_CONTRACT_ID: errors.append("semantic compiler contract mismatch")
    if compiler.get("authority") != "PROPOSAL_ONLY": errors.append("semantic compiler authority boundary mismatch")
    reasoning = PUBLIC_API_CONTRACT.get("reasoning") or {}
    if reasoning.get("artifact_contract_id") != REASONING_ARTIFACT_CONTRACT_ID: errors.append("reasoning artifact contract mismatch")
    if reasoning.get("admission_contract_id") != EPISTEMIC_ADMISSION_CONTRACT_ID: errors.append("epistemic admission contract mismatch")
    if reasoning.get("durability_boundary") != "AASM_EVIDENCE_EVENT_REDUCER_ONLY": errors.append("reasoning durability boundary mismatch")
    if reasoning.get("dependency_truth_maintenance") != "RESERVED_FOR_V0.38": errors.append("reasoning release boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


__all__ = list(dict.fromkeys(["__version__", *getattr(_v31, "__all__", []), *_NEW_IMPORTS]))
