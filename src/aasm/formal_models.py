from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_protocol import (
    TYPED_PROTOCOL_CONTRACT_ID, TYPED_PROTOCOL_CONTRACT_VERSION,
    CAPABILITY_ABI_CONTRACT_ID, CAPABILITY_ABI_CONTRACT_VERSION,
    FORMAL_STATEMENT_CONTRACT_ID, FORMAL_STATEMENT_CONTRACT_VERSION,
    FORMAL_VERIFICATION_CONTRACT_ID, FORMAL_VERIFICATION_CONTRACT_VERSION,
    CAPABILITY_TYPES, FORMAL_LOGICS, FORMAL_QUERY_MODES, FORMAL_RESULT_STATUSES,
    VERIFICATION_STRENGTHS, DISAGREEMENT_POLICIES, _SZS_RE, _jsonable, _uniq,
    _require_nonempty, TypedEventSchema, ScopedLegalTransition, PatternMachine,
    CapabilityContract, CapabilityProvider,
)


@dataclass(frozen=True)
class FormalStatement:
    logic: str
    query_mode: str
    canonical_source: str
    query_encoding: str = ""
    source_artifact_ids: tuple[str, ...] = ()
    source_artifact_fingerprints: dict[str, str] = field(default_factory=dict)
    declarations: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    conjecture: str = ""
    compiler_id: str = "explicit"
    compiler_version: str = "1"
    environment_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    formal_statement_id: str = ""

    def __post_init__(self):
        if self.logic not in FORMAL_LOGICS: raise ValueError(f"unsupported formal logic: {self.logic}")
        if self.query_mode not in FORMAL_QUERY_MODES: raise ValueError(f"unsupported formal query mode: {self.query_mode}")
        _require_nonempty(self.canonical_source, "canonical_source")
        encoding = self.query_encoding
        if not encoding:
            if self.logic == "smtlib2" and self.query_mode in {"VALIDITY", "INVARIANT", "EQUIVALENCE"}: encoding = "ASSUMPTIONS_AND_NEGATED_CONJECTURE"
            elif self.logic == "tptp" and self.query_mode in {"VALIDITY", "INVARIANT", "EQUIVALENCE"}: encoding = "CONJECTURE_STATUS"
            elif self.logic == "lean4": encoding = "KERNEL_CHECK"
            else: encoding = "DIRECT"
        if self.logic == "smtlib2" and self.query_mode in {"VALIDITY", "INVARIANT", "EQUIVALENCE"} and encoding != "ASSUMPTIONS_AND_NEGATED_CONJECTURE":
            raise ValueError("SMT validity/invariant/equivalence requires ASSUMPTIONS_AND_NEGATED_CONJECTURE encoding")
        if self.logic == "lean4" and encoding != "KERNEL_CHECK": raise ValueError("Lean formal statements require KERNEL_CHECK encoding")
        object.__setattr__(self, "query_encoding", encoding)
        _require_nonempty(self.compiler_id, "compiler_id"); _require_nonempty(self.compiler_version, "compiler_version")
        ids = _uniq(self.source_artifact_ids)
        fingerprints = {str(k): str(v) for k, v in sorted(self.source_artifact_fingerprints.items())}
        if fingerprints and set(fingerprints) != set(ids): raise ValueError("source_artifact_fingerprints must exactly match source_artifact_ids")
        object.__setattr__(self, "source_artifact_ids", ids); object.__setattr__(self, "source_artifact_fingerprints", fingerprints)
        object.__setattr__(self, "declarations", tuple(str(v) for v in self.declarations)); object.__setattr__(self, "assumptions", tuple(str(v) for v in self.assumptions)); _jsonable(self.metadata)
        if not self.formal_statement_id: object.__setattr__(self, "formal_statement_id", f"formal-statement-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def source_fingerprint(self) -> str:
        return semantic_fingerprint({"source_artifact_ids": list(self.source_artifact_ids), "source_artifact_fingerprints": dict(self.source_artifact_fingerprints)})
    def identity_payload(self) -> dict[str, Any]:
        return {"logic": self.logic, "query_mode": self.query_mode, "canonical_source": self.canonical_source, "query_encoding": self.query_encoding, "source_artifact_ids": list(self.source_artifact_ids), "source_artifact_fingerprints": dict(self.source_artifact_fingerprints), "declarations": list(self.declarations), "assumptions": list(self.assumptions), "conjecture": self.conjecture, "compiler_id": self.compiler_id, "compiler_version": self.compiler_version, "environment_fingerprint": self.environment_fingerprint, "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"formal_statement_id": self.formal_statement_id, **self.identity_payload()})
    def to_dict(self) -> dict[str, Any]: return {"formal_statement_id": self.formal_statement_id, **self.identity_payload(), "source_fingerprint": self.source_fingerprint, "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormalStatement":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); payload.pop("source_fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class FormalVerificationPolicy:
    policy_id: str = "formal.default"
    required_independent_results: int = 1
    certificate_required: bool = False
    trusted_kernel_required: bool = False
    solver_identity_required: bool = True
    disagreement_policy: str = "INCONCLUSIVE"
    def __post_init__(self):
        _require_nonempty(self.policy_id, "formal verification policy_id")
        if int(self.required_independent_results) < 1: raise ValueError("required_independent_results must be >= 1")
        if self.disagreement_policy not in DISAGREEMENT_POLICIES: raise ValueError("invalid formal disagreement policy")
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass(frozen=True)
class FormalVerificationRequest:
    formal_statement: FormalStatement | dict[str, Any]
    capability_id: str
    capability_version: str
    obligation_id: str
    timeout_ms: int = 30_000
    required_providers: tuple[str, ...] = ()
    policy: FormalVerificationPolicy | dict[str, Any] = field(default_factory=FormalVerificationPolicy)
    linked_artifact_id: str | None = None
    verifier_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    def __post_init__(self):
        statement = self.formal_statement if isinstance(self.formal_statement, FormalStatement) else FormalStatement.from_dict(self.formal_statement)
        policy = self.policy if isinstance(self.policy, FormalVerificationPolicy) else FormalVerificationPolicy(**deepcopy(self.policy))
        object.__setattr__(self, "formal_statement", statement); object.__setattr__(self, "policy", policy)
        _require_nonempty(self.capability_id, "capability_id"); _require_nonempty(self.capability_version, "capability_version"); _require_nonempty(self.obligation_id, "obligation_id")
        if int(self.timeout_ms) <= 0: raise ValueError("formal timeout_ms must be positive")
        object.__setattr__(self, "required_providers", _uniq(self.required_providers)); object.__setattr__(self, "verifier_id", self.verifier_id or f"formal:{self.capability_id}@{self.capability_version}"); _jsonable(self.metadata)
        if not self.request_id: object.__setattr__(self, "request_id", f"formal-request-{semantic_fingerprint(self.identity_payload())[:20]}")
    def identity_payload(self) -> dict[str, Any]:
        return {"formal_statement": self.formal_statement.to_dict(), "capability_id": self.capability_id, "capability_version": self.capability_version, "obligation_id": self.obligation_id, "timeout_ms": int(self.timeout_ms), "required_providers": list(self.required_providers), "policy": self.policy.to_dict(), "linked_artifact_id": self.linked_artifact_id, "verifier_id": self.verifier_id, "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"request_id": self.request_id, **self.identity_payload()})
    @property
    def capability_token(self) -> str: return f"aasm.capability:{self.capability_id}@{self.capability_version}"
    def to_dict(self) -> dict[str, Any]: return {"request_id": self.request_id, **self.identity_payload(), "capability_token": self.capability_token, "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormalVerificationRequest":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); payload.pop("capability_token", None); return cls(**payload)


@dataclass(frozen=True)
class SolverIdentity:
    solver_id: str
    version: str = "unknown"
    binary_sha256: str = ""
    container_digest: str = ""
    invocation: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        _require_nonempty(self.solver_id, "solver_id"); object.__setattr__(self, "invocation", tuple(str(v) for v in self.invocation)); _jsonable(self.metadata)
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.to_dict())
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class FormalVerificationResult:
    request_id: str
    request_fingerprint: str
    formal_statement_fingerprint: str
    canonical_status: str
    solver: SolverIdentity | dict[str, Any]
    raw_status: str
    time_ms: int
    verification_strength: str = "SOLVER_VERDICT"
    proof_object_sha256: str = ""
    counterexample: dict[str, Any] | None = None
    diagnostics: tuple[str, ...] = ()
    raw_output_sha256: str = ""
    certificate_checked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    result_id: str = ""
    def __post_init__(self):
        solver = self.solver if isinstance(self.solver, SolverIdentity) else SolverIdentity(**deepcopy(self.solver)); object.__setattr__(self, "solver", solver)
        for name, value in (("request_id", self.request_id), ("request_fingerprint", self.request_fingerprint), ("formal_statement_fingerprint", self.formal_statement_fingerprint), ("raw_status", self.raw_status)): _require_nonempty(value, name)
        if self.canonical_status not in FORMAL_RESULT_STATUSES: raise ValueError(f"invalid formal result status: {self.canonical_status}")
        if self.verification_strength not in VERIFICATION_STRENGTHS: raise ValueError(f"invalid verification strength: {self.verification_strength}")
        if int(self.time_ms) < 0: raise ValueError("formal result time_ms must be non-negative")
        object.__setattr__(self, "diagnostics", tuple(str(v) for v in self.diagnostics)); _jsonable(self.counterexample); _jsonable(self.metadata)
        if not self.result_id: object.__setattr__(self, "result_id", f"formal-result-{semantic_fingerprint(self.identity_payload())[:20]}")
    def identity_payload(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "request_fingerprint": self.request_fingerprint, "formal_statement_fingerprint": self.formal_statement_fingerprint, "canonical_status": self.canonical_status, "solver": self.solver.to_dict(), "raw_status": self.raw_status, "time_ms": int(self.time_ms), "verification_strength": self.verification_strength, "proof_object_sha256": self.proof_object_sha256, "counterexample": _jsonable(self.counterexample), "diagnostics": list(self.diagnostics), "raw_output_sha256": self.raw_output_sha256, "certificate_checked": bool(self.certificate_checked), "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})
    def to_dict(self) -> dict[str, Any]: return {"result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FormalVerificationResult":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


def typed_protocol_contract() -> dict[str, Any]:
    return {"contract_id": TYPED_PROTOCOL_CONTRACT_ID, "contract_version": TYPED_PROTOCOL_CONTRACT_VERSION, "pattern_admission": "POLICY_OR_CONTROLLER", "transition_proposal": "DECISION_RECORD", "guard_compilation": "ORDINARY_OBLIGATIONS", "transition_activation": "POLICY_OR_CONTROLLER_AFTER_OBLIGATIONS", "direct_pattern_register": "REJECTED", "durability_boundary": "AASM_EVENT_REDUCER_ONLY"}


def capability_abi_contract() -> dict[str, Any]:
    return {"contract_id": CAPABILITY_ABI_CONTRACT_ID, "contract_version": CAPABILITY_ABI_CONTRACT_VERSION, "capability_types": list(CAPABILITY_TYPES), "provider_admission": "POLICY_OR_CONTROLLER", "scheduler_binding": "RESOURCE_CAPABILITY_TOKEN", "lease_boundary": "AASM_TASK_LEASE", "direct_provider_execution": "NOT_AN_AUTHORITY_PATH", "durability_boundary": "AASM_EVENT_REDUCER_ONLY"}


def formal_verification_contract() -> dict[str, Any]:
    return {"contract_id": FORMAL_VERIFICATION_CONTRACT_ID, "contract_version": FORMAL_VERIFICATION_CONTRACT_VERSION, "formal_statement_contract_id": FORMAL_STATEMENT_CONTRACT_ID, "formal_statement_contract_version": FORMAL_STATEMENT_CONTRACT_VERSION, "logics": list(FORMAL_LOGICS), "query_modes": list(FORMAL_QUERY_MODES), "result_statuses": list(FORMAL_RESULT_STATUSES), "verification_strengths": list(VERIFICATION_STRENGTHS), "formalization_authority": "PROPOSAL_ONLY", "solver_authority": "EVIDENCE_ONLY", "epistemic_authority": "V37_POLICY_ADMISSION", "solver_voting": "NOT_TRUTH", "raw_output_policy": "DIAGNOSTIC_HASH_NOT_SEMANTIC_IDENTITY", "proof_object_policy": "CONTENT_HASHED_SEPARATELY", "source_translation_policy": "FINGERPRINTED_FORMALIZATION_REQUIRED", "default_solver_identity_policy": "VERSION_AND_BINARY_SHA256_OR_CONTAINER_DIGEST", "smt_validity_encoding": "ASSUMPTIONS_AND_NEGATED_CONJECTURE", "lean_rejection": "NOT_A_REFUTATION"}


def pattern_document(value) -> str: return canonical_semantic_json(value.to_dict())

def parse_vampire_status(output: str) -> str:
    match = _SZS_RE.search(output or ""); return match.group(1) if match else "Unknown"

def parse_smt_status(output: str) -> str:
    for line in (output or "").splitlines():
        token = line.strip().lower()
        if not token or token.startswith(";"): continue
        if token in {"sat", "unsat", "unknown"}: return token
        break
    return "unknown"


def canonicalize_solver_status(query_mode: str, solver_id: str, raw_status: str, *, returncode: int = 0) -> str:
    if query_mode not in FORMAL_QUERY_MODES: raise ValueError(query_mode)
    solver_id, lower = solver_id.lower(), str(raw_status).strip().lower()
    if solver_id in {"z3", "cvc5"}:
        if lower == "unknown": return "UNKNOWN"
        if query_mode in {"VALIDITY", "INVARIANT", "EQUIVALENCE"}: return "PROVED" if lower == "unsat" else "COUNTERMODEL" if lower == "sat" else "UNKNOWN"
        if query_mode == "SATISFIABILITY": return "SAT" if lower == "sat" else "UNSAT" if lower == "unsat" else "UNKNOWN"
        if query_mode == "COUNTERMODEL": return "COUNTERMODEL" if lower == "sat" else "UNSAT" if lower == "unsat" else "UNKNOWN"
    if solver_id == "vampire":
        theorem, counter = {"theorem", "unsatisfiable", "contradictoryaxioms"}, {"countersatisfiable", "satisfiable"}
        if query_mode in {"VALIDITY", "INVARIANT", "EQUIVALENCE"}: return "PROVED" if lower in theorem else "COUNTERMODEL" if lower in counter else "UNKNOWN"
        if query_mode == "SATISFIABILITY": return "SAT" if lower in counter else "UNSAT" if lower in theorem else "UNKNOWN"
        if query_mode == "COUNTERMODEL": return "COUNTERMODEL" if lower in counter else "UNSAT" if lower in theorem else "UNKNOWN"
    if solver_id in {"lean", "lean4"}: return "PROVED" if returncode == 0 and lower in {"accepted", "ok", "proved"} else "UNKNOWN"
    if lower == "timeout": return "TIMEOUT"
    if lower == "error": return "ERROR"
    return "UNKNOWN"


def default_formal_capability_contracts() -> tuple[CapabilityContract, ...]:
    inp = {"type": "object", "required": ["request_id", "formal_statement"], "properties": {"request_id": {"type": "string", "minLength": 1}, "formal_statement": {"type": "object"}}}
    out = {"type": "object", "required": ["canonical_status", "solver"], "properties": {"canonical_status": {"type": "string", "enum": list(FORMAL_RESULT_STATUSES)}, "solver": {"type": "object"}}}
    return (
        CapabilityContract("formal.first_order", "VERIFIER", "0.1.0", inp, out, ("tptp",), FORMAL_QUERY_MODES, ("formal_verification_result",)),
        CapabilityContract("formal.smt", "VERIFIER", "0.1.0", inp, out, ("smtlib2",), FORMAL_QUERY_MODES, ("formal_verification_result",)),
        CapabilityContract("formal.proof_kernel", "VERIFIER", "0.1.0", inp, out, ("lean4",), ("VALIDITY", "INVARIANT", "EQUIVALENCE"), ("formal_verification_result",)),
        CapabilityContract("formal.certificate_checker", "VERIFIER", "0.1.0", inp, out, FORMAL_LOGICS, FORMAL_QUERY_MODES, ("formal_verification_result",)),
    )


def default_formal_providers() -> tuple[CapabilityProvider, ...]:
    return (
        CapabilityProvider("vampire", "formal.first_order", "0.1.0", "formal-vampire", "vampire", ("tptp",), FORMAL_QUERY_MODES),
        CapabilityProvider("z3", "formal.smt", "0.1.0", "formal-z3", "z3", ("smtlib2",), FORMAL_QUERY_MODES),
        CapabilityProvider("cvc5", "formal.smt", "0.1.0", "formal-cvc5", "cvc5", ("smtlib2",), FORMAL_QUERY_MODES),
        CapabilityProvider("lean4", "formal.proof_kernel", "0.1.0", "formal-lean4", "lean", ("lean4",), ("VALIDITY", "INVARIANT", "EQUIVALENCE")),
    )


__all__ = ["FormalStatement", "FormalVerificationPolicy", "FormalVerificationRequest", "SolverIdentity", "FormalVerificationResult", "typed_protocol_contract", "capability_abi_contract", "formal_verification_contract", "pattern_document", "parse_vampire_status", "parse_smt_status", "canonicalize_solver_status", "default_formal_capability_contracts", "default_formal_providers"]
