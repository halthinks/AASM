from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol, runtime_checkable

from .profile_packages import ADAPTER_ROLES, AdapterBinding, canonical_hash, canonical_json
from .semantic_result import (
    DomainPackage,
    ProblemDefinition,
    ProblemInstance,
    ProblemModel,
    build_problem_instance,
    canonical_semantic_json,
    semantic_fingerprint,
    validate_problem_instance,
    validate_problem_model,
)

ADAPTER_METHODS = {
    "decision_backend": "propose",
    "obligation_adapter": "derive",
    "semantic_validator": "evaluate",
    "conflict_explainer": "explain",
    "constraint_certifier": "certify",
}

SEMANTIC_SOURCE_CONTRACT_ID = "aasm.semantic.source.v1"
SEMANTIC_SOURCE_CONTRACT_VERSION = "0.1.0"
SEMANTIC_COMPILER_CONTRACT_ID = "aasm.semantic.compiler.v1"
SEMANTIC_COMPILER_CONTRACT_VERSION = "0.1.0"
COMPILER_STAGES = (
    "PARSE", "RESOLVE", "NORMALIZE", "TYPE_CHECK", "VALIDATE", "FINGERPRINT", "INSTANTIATE"
)
COMPILER_AUTHORITIES = {"PROPOSAL_ONLY"}


@dataclass
class DecisionRequest:
    machine_id: str
    profile_binding: dict[str, Any]
    active_model: dict[str, str]
    available_decisions: list[dict[str, Any]]
    hard_constraints: list[dict[str, Any]] = field(default_factory=list)
    soft_constraints: list[dict[str, Any]] = field(default_factory=list)
    overdue_obligation_ids: list[str] = field(default_factory=list)
    resource_budget: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    strategy_state: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.machine_id: raise ValueError("DecisionRequest.machine_id is required")
        self.overdue_obligation_ids = sorted(set(self.overdue_obligation_ids))
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class CandidateModel:
    candidate_id: str
    assignments: dict[str, str]
    backend_id: str
    backend_version: str
    rationale: dict[str, Any] = field(default_factory=dict)
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.candidate_id or not self.backend_id or not self.backend_version:
            raise ValueError("candidate_id, backend_id, and backend_version are required")
        if not isinstance(self.assignments, dict): raise ValueError("candidate assignments must be an object mapping subjects to decision IDs")
        for subject, decision_id in self.assignments.items():
            if not str(subject) or not str(decision_id): raise ValueError("candidate assignments require non-empty subjects and decision IDs")
    def to_dict(self) -> dict[str, Any]: return asdict(self)
    @property
    def fingerprint(self) -> str: return canonical_hash(self.to_dict())
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateModel": return cls(**deepcopy(data))


@dataclass
class CandidateValidationReport:
    candidate_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    violated_constraint_ids: list[str] = field(default_factory=list)
    overdue_obligation_ids: list[str] = field(default_factory=list)
    normalized_assignments: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.errors = list(dict.fromkeys(self.errors)); self.warnings = list(dict.fromkeys(self.warnings))
        self.violated_constraint_ids = sorted(set(self.violated_constraint_ids)); self.overdue_obligation_ids = sorted(set(self.overdue_obligation_ids))
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class DomainContext:
    machine_id: str
    profile_binding: dict[str, Any]
    configuration: dict[str, Any] = field(default_factory=dict)
    state_view: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.machine_id: raise ValueError("DomainContext.machine_id is required")
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ValidationContext:
    domain: DomainContext
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    prior_results: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ExplanationContext:
    domain: DomainContext
    conflict: dict[str, Any]
    active_model_snapshot: dict[str, str]
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    dependency_view: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ExplanationCandidate:
    explanation_id: str
    conflict_id: str
    method: str
    assumption_literals: list[dict[str, Any]]
    evidence_ids: list[str]
    scope: dict[str, Any] = field(default_factory=dict)
    certificate: dict[str, Any] = field(default_factory=dict)
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.explanation_id or not self.conflict_id or not self.method: raise ValueError("explanation_id, conflict_id, and method are required")
        if not self.assumption_literals: raise ValueError("explanation candidate requires assumption literals")
        self.evidence_ids = sorted(set(self.evidence_ids))
        if not self.evidence_ids: raise ValueError("explanation candidate requires evidence")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0: raise ValueError("confidence must be between 0 and 1")
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class CertificationContext:
    domain: DomainContext
    conflict: dict[str, Any]
    explanation: dict[str, Any]
    proposed_constraint: dict[str, Any]
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ConstraintCertificate:
    certificate_id: str
    level: str
    authority: str
    evidence_ids: list[str]
    valid: bool
    scope: dict[str, Any] = field(default_factory=dict)
    artifact_hash: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.certificate_id or not self.authority: raise ValueError("certificate_id and authority are required")
        if self.level not in {"PROVEN", "VALIDATED", "CORROBORATED", "PROVISIONAL", "HEURISTIC", "REJECTED"}: raise ValueError(f"invalid certificate level: {self.level}")
        self.evidence_ids = sorted(set(self.evidence_ids))
        if self.valid and not self.evidence_ids: raise ValueError("a valid constraint certificate requires evidence")
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@runtime_checkable
class DecisionBackend(Protocol):
    def propose(self, request: DecisionRequest) -> CandidateModel | dict[str, Any]: ...

@runtime_checkable
class ObligationAdapter(Protocol):
    def derive(self, model: CandidateModel, context: DomainContext) -> list[Any]: ...

@runtime_checkable
class SemanticValidator(Protocol):
    def evaluate(self, obligation: Any, context: ValidationContext) -> Any: ...

@runtime_checkable
class ConflictExplainer(Protocol):
    def explain(self, conflict: Any, context: ExplanationContext) -> ExplanationCandidate | dict[str, Any]: ...

@runtime_checkable
class ConstraintCertifier(Protocol):
    def certify(self, constraint: Any, context: CertificationContext) -> ConstraintCertificate | dict[str, Any]: ...


def adapter_method(role: str) -> str:
    if role not in ADAPTER_ROLES: raise ValueError(f"unknown adapter role: {role}")
    return ADAPTER_METHODS[role]


def validate_adapter_object(role: str, adapter: Any) -> list[str]:
    errors: list[str] = []
    try: method_name = adapter_method(role)
    except ValueError as exc: return [str(exc)]
    if not callable(getattr(adapter, method_name, None)): errors.append(f"adapter for {role} must expose callable {method_name}()")
    return errors


def load_adapter(binding: AdapterBinding, *, allow_import: bool = False) -> Any:
    if not allow_import: raise PermissionError("adapter import requires explicit allow_import=True")
    module_name, attribute = binding.target.split(":", 1); module = importlib.import_module(module_name); value = getattr(module, attribute)
    adapter = value(binding.config) if isinstance(value, type) else value
    errors = validate_adapter_object(binding.role, adapter)
    if errors: raise TypeError("; ".join(errors))
    return adapter


def determinism_probe(adapter: Any, role: str, payload: tuple[Any, ...]) -> tuple[bool, str | None]:
    errors = validate_adapter_object(role, adapter)
    if errors: return False, "; ".join(errors)
    method = getattr(adapter, adapter_method(role))
    first = method(*deepcopy(payload)); second = method(*deepcopy(payload))
    if canonical_json(first) != canonical_json(second): return False, "adapter returned different results for identical isolated fixtures"
    return True, None


# --------------------------- v0.36 Semantic Compiler SDK ---------------------------

@dataclass(frozen=True)
class CompilerDeclaration:
    compiler_id: str = "aasm.reference.semantic-compiler"
    compiler_version: str = "0.1.0"
    source_contract_id: str = SEMANTIC_SOURCE_CONTRACT_ID
    source_contract_version: str = SEMANTIC_SOURCE_CONTRACT_VERSION
    stages: tuple[str, ...] = COMPILER_STAGES
    deterministic: bool = True
    authority: str = "PROPOSAL_ONLY"
    admission_boundary: str = "AASM_EVENT_REDUCER_ONLY"
    def __post_init__(self):
        if not self.compiler_id or not self.compiler_version: raise ValueError("compiler identity and version are required")
        if self.authority not in COMPILER_AUTHORITIES: raise ValueError("semantic compiler must remain PROPOSAL_ONLY")
        if tuple(self.stages) != COMPILER_STAGES: raise ValueError("reference compiler stages are fixed and ordered")
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(asdict(self))
    def to_dict(self) -> dict[str, Any]:
        out = asdict(self); out["fingerprint"] = self.fingerprint; return out


@dataclass(frozen=True)
class EnvironmentSnapshot:
    inputs: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = "aasm.semantic.environment.v1"
    contract_version: str = "0.1.0"
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(asdict(self))
    def to_dict(self) -> dict[str, Any]:
        out = asdict(self); out["fingerprint"] = self.fingerprint; return out


@dataclass(frozen=True)
class RawProblemInput:
    source_name: str
    document: dict[str, Any]
    source_text: str = ""
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.document)
    def to_dict(self) -> dict[str, Any]: return {"source_name": self.source_name, "document": deepcopy(self.document), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class CompilerDiagnostic:
    issue_code: str
    message: str
    stage: str
    severity: str
    source_name: str
    json_pointer: str = ""
    line: int = 1
    column: int = 1
    byte_offset: int = 0
    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class CompileResult:
    status: str
    problem_instance: ProblemInstance | None = None
    domain_package: DomainPackage | None = None
    problem_definition: ProblemDefinition | None = None
    problem_model: ProblemModel | None = None
    missing_inputs: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    warnings: list[CompilerDiagnostic] = field(default_factory=list)
    hard_errors: list[CompilerDiagnostic] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)
    cache_key: str = ""
    cache_hit: bool = False
    fingerprint: str = ""

    def __post_init__(self):
        self.missing_inputs = sorted(set(self.missing_inputs)); self.missing_capabilities = sorted(set(self.missing_capabilities))
        if not self.fingerprint: self.fingerprint = semantic_fingerprint(self._fingerprint_payload())
    def _fingerprint_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "problem_instance": self.problem_instance.to_dict() if self.problem_instance else None,
            "domain_package": self.domain_package.to_dict() if self.domain_package else None,
            "problem_definition": self.problem_definition.to_dict() if self.problem_definition else None,
            "problem_model": self.problem_model.to_dict() if self.problem_model else None,
            "missing_inputs": self.missing_inputs,
            "missing_capabilities": self.missing_capabilities,
            "warnings": [row.to_dict() for row in self.warnings],
            "hard_errors": [row.to_dict() for row in self.hard_errors],
            "audit_trail": self.audit_trail,
            "cache_key": self.cache_key,
        }
    def to_dict(self) -> dict[str, Any]:
        return {**self._fingerprint_payload(), "cache_hit": self.cache_hit, "fingerprint": self.fingerprint}


@runtime_checkable
class DomainCompiler(Protocol):
    declaration: CompilerDeclaration
    def compile_domain(self, request: RawProblemInput) -> DomainPackage: ...


@runtime_checkable
class InstanceCompiler(Protocol):
    declaration: CompilerDeclaration
    def compile_instance(self, domain: DomainPackage, request: RawProblemInput, environment: EnvironmentSnapshot) -> CompileResult: ...


class CompilationCache:
    def __init__(self): self._records: dict[str, CompileResult] = {}
    def get(self, key: str) -> CompileResult | None:
        value = self._records.get(key); return deepcopy(value) if value is not None else None
    def put(self, key: str, result: CompileResult) -> None:
        existing = self._records.get(key)
        if existing is not None and existing.fingerprint != result.fingerprint:
            raise RuntimeError(f"semantic compiler cache collision for {key}")
        self._records[key] = deepcopy(result)
    def __len__(self) -> int: return len(self._records)


def semantic_compiler_contract() -> dict[str, Any]:
    declaration = CompilerDeclaration()
    return {
        "contract_id": SEMANTIC_COMPILER_CONTRACT_ID,
        "contract_version": SEMANTIC_COMPILER_CONTRACT_VERSION,
        "source_contract_id": SEMANTIC_SOURCE_CONTRACT_ID,
        "source_contract_version": SEMANTIC_SOURCE_CONTRACT_VERSION,
        "stages": list(COMPILER_STAGES),
        "authority": declaration.authority,
        "admission_boundary": declaration.admission_boundary,
        "deterministic_id_rule": "SHA256_NORMALIZED_INPUT_DOMAIN_COMPILER",
        "cache_key": "COMPILER_DECLARATION_PLUS_CANONICAL_SOURCE_PLUS_ENVIRONMENT_PLUS_POLICY",
        "diagnostics": ["json_pointer", "line", "column", "utf8_byte_offset", "stage", "severity", "issue_code"],
    }


def _clean_fingerprint(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(k): _clean_fingerprint(v) for k, v in value.items() if k != "fingerprint"}
    if isinstance(value, list): return [_clean_fingerprint(v) for v in value]
    return deepcopy(value)


def _location(text: str, pointer: str) -> tuple[int, int, int]:
    if not text: return 1, 1, 0
    token = pointer.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~") if pointer else ""
    needle = json.dumps(token, ensure_ascii=False) if token else ""
    index = text.find(needle) if needle else 0
    if index < 0: index = 0
    line = text.count("\n", 0, index) + 1
    last = text.rfind("\n", 0, index); column = index + 1 if last < 0 else index - last
    return line, column, len(text[:index].encode("utf-8"))


def _diagnostic(request: RawProblemInput, stage: str, code: str, message: str, pointer: str = "", severity: str = "ERROR") -> CompilerDiagnostic:
    line, column, byte_offset = _location(request.source_text, pointer)
    return CompilerDiagnostic(code, message, stage, severity, request.source_name, pointer, line, column, byte_offset)


def _audit(stages: Mapping[str, str]) -> list[dict[str, Any]]:
    return [{"stage": stage, "status": stages.get(stage, "SKIPPED")} for stage in COMPILER_STAGES]


def _load_source(source: Any, source_name: str | None = None) -> tuple[RawProblemInput | None, CompilerDiagnostic | None]:
    if isinstance(source, Mapping):
        document = deepcopy(dict(source)); text = canonical_semantic_json(document)
        return RawProblemInput(source_name or "<mapping>", document, text), None
    if isinstance(source, bytes):
        text = source.decode("utf-8"); name = source_name or "<bytes>"
    else:
        candidate = str(source); name = source_name or "<string>"; text = candidate
        try:
            path = Path(candidate)
            if len(candidate) < 4096 and path.is_file(): name = source_name or str(path); text = path.read_text(encoding="utf-8")
        except (OSError, ValueError): pass
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        diagnostic = CompilerDiagnostic(
            "SOURCE_JSON_INVALID", exc.msg, "PARSE", "ERROR", name, "",
            int(exc.lineno), int(exc.colno), len(text[: exc.pos].encode("utf-8")),
        )
        return None, diagnostic
    if not isinstance(document, dict):
        request = RawProblemInput(name, {}, text)
        return None, _diagnostic(request, "PARSE", "SOURCE_ROOT_NOT_OBJECT", "semantic source root must be an object")
    return RawProblemInput(name, document, text), None


class ReferenceSemanticCompiler:
    declaration = CompilerDeclaration()

    def compile_domain(self, request: RawProblemInput) -> DomainPackage:
        raw = request.document.get("domain_package")
        if not isinstance(raw, Mapping): raise ValueError("domain_package is required and must be an object")
        return DomainPackage(**_clean_fingerprint(raw))

    def compile_instance(self, domain: DomainPackage, request: RawProblemInput, environment: EnvironmentSnapshot) -> CompileResult:
        stages = {stage: "SKIPPED" for stage in COMPILER_STAGES}
        for stage in ("PARSE", "RESOLVE", "NORMALIZE"): stages[stage] = "PASS"
        errors: list[CompilerDiagnostic] = []
        document = request.document
        try:
            definition_raw = document.get("problem_definition")
            model_raw = document.get("problem_model")
            if not isinstance(definition_raw, Mapping): raise ValueError("problem_definition is required and must be an object")
            if not isinstance(model_raw, Mapping): raise ValueError("problem_model is required and must be an object")
            definition = ProblemDefinition(**_clean_fingerprint(definition_raw))
            model = ProblemModel(**_clean_fingerprint(model_raw))
            stages["TYPE_CHECK"] = "PASS"
        except Exception as exc:
            errors.append(_diagnostic(request, "TYPE_CHECK", "SEMANTIC_TYPE_ERROR", str(exc), "/problem_model"))
            stages["TYPE_CHECK"] = "FAIL"
            return CompileResult("FAIL", domain_package=domain, hard_errors=errors, audit_trail=_audit(stages))

        model_report = validate_problem_model(domain, definition, model)
        for message in model_report["errors"]:
            errors.append(_diagnostic(request, "VALIDATE", "MODEL_VALIDATION_ERROR", message, "/problem_model"))
        if errors:
            stages["VALIDATE"] = "FAIL"
            return CompileResult("FAIL", domain_package=domain, problem_definition=definition, problem_model=model, hard_errors=errors, audit_trail=_audit(stages))
        stages["VALIDATE"] = "PASS"

        required_inputs = sorted(set(str(item) for item in (document.get("required_inputs") or [])))
        inline_inputs = dict(document.get("inputs") or {})
        available_inputs = {**environment.inputs, **inline_inputs}
        missing_inputs = [item for item in required_inputs if item not in available_inputs]
        if missing_inputs:
            stages["FINGERPRINT"] = "PASS"
            return CompileResult(
                "BLOCKED_MISSING_INPUTS", domain_package=domain, problem_definition=definition,
                problem_model=model, missing_inputs=missing_inputs, audit_trail=_audit(stages),
            )

        spec = dict(document.get("instance") or {})
        capability_bindings = {**environment.capabilities, **dict(spec.get("capability_bindings") or {})}
        id_material = {
            "source_id": document.get("source_id"), "source_version": document.get("source_version"),
            "domain_fingerprint": domain.fingerprint, "definition_fingerprint": definition.to_dict()["fingerprint"],
            "model_fingerprint": model.fingerprint, "instance": _clean_fingerprint(spec), "inputs": available_inputs,
            "compiler": self.declaration.to_dict(),
        }
        instance_id = str(spec.get("instance_id") or f"instance-{semantic_fingerprint(id_material)[:16]}")
        stages["FINGERPRINT"] = "PASS"
        instance = build_problem_instance(
            domain, definition, model, instance_id=instance_id,
            decision_variables=dict(spec.get("decision_variables") or {}),
            facts=tuple(spec.get("facts") or ()), assumptions=tuple(spec.get("assumptions") or ()),
            obligations=tuple(spec.get("obligations") or ()), constraints=tuple(spec.get("constraints") or ()),
            capability_bindings=capability_bindings, completion_rule=dict(spec.get("completion_rule") or {}),
            metadata={**dict(spec.get("metadata") or {}), "compiler_id": self.declaration.compiler_id,
                      "compiler_version": self.declaration.compiler_version, "normalized_inputs": available_inputs},
        )
        stages["INSTANTIATE"] = "PASS"
        validation = validate_problem_instance(domain, definition, model, instance)
        hard_errors = [
            _diagnostic(request, "INSTANTIATE", "INSTANCE_VALIDATION_ERROR", message, "/instance")
            for message in validation["errors"]
            if instance.compile_status not in {"BLOCKED_MISSING_CAPABILITIES"}
        ]
        missing_capabilities = sorted(
            item.split(":", 1)[1] for item in instance.unresolved_specification if str(item).startswith("capability:")
        )
        if hard_errors: status = "FAIL"
        elif missing_capabilities: status = "BLOCKED_MISSING_CAPABILITIES"
        else: status = "PASS"
        return CompileResult(
            status, problem_instance=instance, domain_package=domain, problem_definition=definition,
            problem_model=model, missing_capabilities=missing_capabilities, hard_errors=hard_errors,
            audit_trail=_audit(stages),
        )


class CompilationCache:
    def __init__(self): self._records: dict[str, CompileResult] = {}
    def get(self, key: str) -> CompileResult | None:
        value = self._records.get(key); return deepcopy(value) if value is not None else None
    def put(self, key: str, result: CompileResult) -> None:
        existing = self._records.get(key)
        if existing is not None and existing.fingerprint != result.fingerprint: raise RuntimeError(f"semantic compiler cache collision for {key}")
        self._records[key] = deepcopy(result)
    def __len__(self) -> int: return len(self._records)


def compile_semantic_source(
    source: Any,
    *,
    compiler: DomainCompiler | InstanceCompiler | None = None,
    environment: EnvironmentSnapshot | None = None,
    cache: CompilationCache | None = None,
    policy: Mapping[str, Any] | None = None,
    source_name: str | None = None,
) -> CompileResult:
    compiler = compiler or ReferenceSemanticCompiler(); environment = environment or EnvironmentSnapshot(); policy = dict(policy or {})
    request, parse_error = _load_source(source, source_name)
    if parse_error is not None: return CompileResult("FAIL", hard_errors=[parse_error], audit_trail=_audit({"PARSE": "FAIL"}))
    assert request is not None
    document = request.document
    resolve_errors: list[CompilerDiagnostic] = []
    if document.get("contract_id") != SEMANTIC_SOURCE_CONTRACT_ID:
        resolve_errors.append(_diagnostic(request, "RESOLVE", "SOURCE_CONTRACT_UNSUPPORTED", f"expected {SEMANTIC_SOURCE_CONTRACT_ID}", "/contract_id"))
    if document.get("contract_version") != SEMANTIC_SOURCE_CONTRACT_VERSION:
        resolve_errors.append(_diagnostic(request, "RESOLVE", "SOURCE_VERSION_UNSUPPORTED", f"expected {SEMANTIC_SOURCE_CONTRACT_VERSION}", "/contract_version"))
    for key in ("domain_package", "problem_definition", "problem_model"):
        if key not in document: resolve_errors.append(_diagnostic(request, "RESOLVE", "SOURCE_MEMBER_MISSING", f"missing required source member: {key}", f"/{key}"))
    if resolve_errors: return CompileResult("FAIL", hard_errors=resolve_errors, audit_trail=_audit({"PARSE": "PASS", "RESOLVE": "FAIL"}))

    declaration = getattr(compiler, "declaration", CompilerDeclaration())
    normalized_source = canonical_semantic_json(_clean_fingerprint(document))
    cache_key = semantic_fingerprint({
        "compiler": declaration.to_dict(), "source": normalized_source,
        "environment": environment.to_dict(), "policy": dict(policy),
    })
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            cached.cache_hit = True
            return cached
    try:
        domain = compiler.compile_domain(request)
        result = compiler.compile_instance(domain, request, environment)
    except Exception as exc:
        result = CompileResult("FAIL", hard_errors=[_diagnostic(request, "TYPE_CHECK", "COMPILER_EXCEPTION", str(exc))], audit_trail=_audit({"PARSE": "PASS", "RESOLVE": "PASS", "NORMALIZE": "PASS", "TYPE_CHECK": "FAIL"}))
    result.cache_key = cache_key
    result.fingerprint = semantic_fingerprint(result._fingerprint_payload())
    if cache is not None: cache.put(cache_key, result)
    return result


def compile_and_admit(
    engine: Any,
    source: Any,
    *,
    compiler: DomainCompiler | InstanceCompiler | None = None,
    environment: EnvironmentSnapshot | None = None,
    cache: CompilationCache | None = None,
    policy: Mapping[str, Any] | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    result = compile_semantic_source(source, compiler=compiler, environment=environment, cache=cache, policy=policy, source_name=source_name)
    if result.problem_instance is None or result.status == "FAIL":
        return {"admitted": False, "compile_result": result.to_dict(), "admission": None}
    admission = engine.admit_semantic_problem(result.domain_package, result.problem_definition, result.problem_model, result.problem_instance)
    return {"admitted": True, "compile_result": result.to_dict(), "admission": admission}


def reference_semantic_source() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_SOURCE_CONTRACT_ID,
        "contract_version": SEMANTIC_SOURCE_CONTRACT_VERSION,
        "source_id": "compiler-conformance",
        "source_version": "1.0.0",
        "domain_package": {
            "package_id": "compiler.example", "version": "1.0.0", "type_registry": {"component": {}},
            "predicate_registry": ["ready"], "required_capabilities": ["compute"],
            "operators": [{"operator_id": "make-ready", "required_capabilities": ["compute"], "effects": [{"predicate_id": "ready"}]}],
            "observers": [{"observer_id": "observe-ready", "outputs": ["ready"]}],
            "verifiers": [{"verifier_id": "verify-ready", "accepts": ["ready"]}],
        },
        "problem_definition": {
            "definition_id": "compiler.problem", "version": "1.0.0",
            "goal": {"predicate_id": "ready", "arguments": ["component-1"], "value": True},
            "required_entity_kinds": ["component"], "required_predicates": ["ready"],
        },
        "problem_model": {
            "model_id": "compiler.model", "version": "1.0.0",
            "entities": [{"entity_id": "component-1", "kind": "component"}],
            "predicates": [{"predicate_id": "ready", "arity": 1, "argument_kinds": ["component"]}],
            "operators": [{"operator_id": "make-ready", "required_capabilities": ["compute"], "effects": [{"predicate_id": "ready"}]}],
            "observers": [{"observer_id": "observe-ready", "outputs": ["ready"]}],
            "verifiers": [{"verifier_id": "verify-ready", "accepts": ["ready"]}],
            "objectives": [{"objective_id": "goal-ready", "predicate_id": "ready"}],
        },
        "instance": {
            "decision_variables": {"mode": {"domain": ["safe", "fast"], "value": "safe"}},
            "facts": [{"predicate_id": "ready", "arguments": ["component-1"], "value": False}],
        },
    }


def run_semantic_compiler_conformance(compiler: DomainCompiler | InstanceCompiler | None = None) -> dict[str, Any]:
    from .model import ProblemSpec
    from .runtime_v32 import AASMEngine
    compiler = compiler or ReferenceSemanticCompiler(); cache = CompilationCache()
    environment = EnvironmentSnapshot(capabilities={"compute": {"kind": "worker"}})
    source = reference_semantic_source()
    first = compile_semantic_source(source, compiler=compiler, environment=environment, cache=cache)
    second = compile_semantic_source(source, compiler=compiler, environment=environment, cache=cache)
    invalid = compile_semantic_source('{"contract_id":', compiler=compiler)
    engine = AASMEngine(ProblemSpec("compiler conformance")); before = len(engine.events)
    admission = compile_and_admit(engine, source, compiler=compiler, environment=environment)
    checks = {
        "valid_source_compiles": first.status == "PASS" and first.problem_instance is not None,
        "repeated_compile_same_fingerprint": first.fingerprint == second.fingerprint,
        "repeated_compile_same_problem_fingerprint": bool(first.problem_instance and second.problem_instance and first.problem_instance.fingerprint == second.problem_instance.fingerprint),
        "cache_reused": second.cache_hit is True and len(cache) == 1,
        "invalid_source_has_mapped_diagnostic": invalid.status == "FAIL" and bool(invalid.hard_errors) and invalid.hard_errors[0].line >= 1 and invalid.hard_errors[0].column >= 1,
        "proposal_only_authority": getattr(compiler, "declaration", CompilerDeclaration()).authority == "PROPOSAL_ONLY",
        "event_sourced_admission": admission["admitted"] is True and len(engine.events) > before and engine.semantic_problem_report().get("configured") is True,
        "admission_boundary_declared": getattr(compiler, "declaration", CompilerDeclaration()).admission_boundary == "AASM_EVENT_REDUCER_ONLY",
    }
    report = {
        "contract_id": SEMANTIC_COMPILER_CONTRACT_ID,
        "contract_version": SEMANTIC_COMPILER_CONTRACT_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "compiler": getattr(compiler, "declaration", CompilerDeclaration()).to_dict(),
        "valid_compile_fingerprint": first.fingerprint,
        "problem_fingerprint": first.problem_instance.fingerprint if first.problem_instance else None,
    }
    report["report_sha256"] = semantic_fingerprint(report)
    return report
