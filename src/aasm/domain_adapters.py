from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import importlib
from typing import Any, Protocol, runtime_checkable

from .profile_packages import ADAPTER_ROLES, AdapterBinding, canonical_hash, canonical_json


ADAPTER_METHODS = {
    "decision_backend": "propose",
    "obligation_adapter": "derive",
    "semantic_validator": "evaluate",
    "conflict_explainer": "explain",
    "constraint_certifier": "certify",
}


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
        if not self.machine_id:
            raise ValueError("DecisionRequest.machine_id is required")
        self.overdue_obligation_ids = sorted(set(self.overdue_obligation_ids))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        if not isinstance(self.assignments, dict):
            raise ValueError("candidate assignments must be an object mapping subjects to decision IDs")
        for subject, decision_id in self.assignments.items():
            if not str(subject) or not str(decision_id):
                raise ValueError("candidate assignments require non-empty subjects and decision IDs")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateModel":
        return cls(**deepcopy(data))


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
        self.errors = list(dict.fromkeys(self.errors))
        self.warnings = list(dict.fromkeys(self.warnings))
        self.violated_constraint_ids = sorted(set(self.violated_constraint_ids))
        self.overdue_obligation_ids = sorted(set(self.overdue_obligation_ids))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainContext:
    machine_id: str
    profile_binding: dict[str, Any]
    configuration: dict[str, Any] = field(default_factory=dict)
    state_view: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.machine_id:
            raise ValueError("DomainContext.machine_id is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationContext:
    domain: DomainContext
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    prior_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExplanationContext:
    domain: DomainContext
    conflict: dict[str, Any]
    active_model_snapshot: dict[str, str]
    evidence_records: list[dict[str, Any]] = field(default_factory=list)
    dependency_view: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        if not self.explanation_id or not self.conflict_id or not self.method:
            raise ValueError("explanation_id, conflict_id, and method are required")
        if not self.assumption_literals:
            raise ValueError("explanation candidate requires assumption literals")
        self.evidence_ids = sorted(set(self.evidence_ids))
        if not self.evidence_ids:
            raise ValueError("explanation candidate requires evidence")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CertificationContext:
    domain: DomainContext
    conflict: dict[str, Any]
    explanation: dict[str, Any]
    proposed_constraint: dict[str, Any]
    evidence_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        if not self.certificate_id or not self.authority:
            raise ValueError("certificate_id and authority are required")
        if self.level not in {
            "PROVEN", "VALIDATED", "CORROBORATED", "PROVISIONAL", "HEURISTIC", "REJECTED"
        }:
            raise ValueError(f"invalid certificate level: {self.level}")
        self.evidence_ids = sorted(set(self.evidence_ids))
        if self.valid and not self.evidence_ids:
            raise ValueError("a valid constraint certificate requires evidence")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    if role not in ADAPTER_ROLES:
        raise ValueError(f"unknown adapter role: {role}")
    return ADAPTER_METHODS[role]


def validate_adapter_object(role: str, adapter: Any) -> list[str]:
    errors: list[str] = []
    try:
        method_name = adapter_method(role)
    except ValueError as exc:
        return [str(exc)]
    method = getattr(adapter, method_name, None)
    if not callable(method):
        errors.append(f"adapter for {role} must expose callable {method_name}()")
    return errors


def load_adapter(binding: AdapterBinding, *, allow_import: bool = False) -> Any:
    """Load an installed adapter only after explicit caller opt-in.

    Profile discovery and validation never import adapter code automatically.
    Loading an adapter is an execution-boundary decision and does not grant the
    adapter permission to mutate AASM state or perform external effects.
    """

    if not allow_import:
        raise PermissionError("adapter import requires explicit allow_import=True")
    module_name, attribute = binding.target.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, attribute)
    adapter = value(binding.config) if isinstance(value, type) else value
    errors = validate_adapter_object(binding.role, adapter)
    if errors:
        raise TypeError("; ".join(errors))
    return adapter


def determinism_probe(adapter: Any, role: str, payload: tuple[Any, ...]) -> tuple[bool, str | None]:
    """Execute a caller-supplied deterministic fixture twice and compare output.

    This is opt-in because adapter execution may be expensive or effectful. A
    conformance caller must supply isolated fixtures and keep external effects
    behind the ordinary AASM effect boundary.
    """

    errors = validate_adapter_object(role, adapter)
    if errors:
        return False, "; ".join(errors)
    method = getattr(adapter, adapter_method(role))
    first = method(*deepcopy(payload))
    second = method(*deepcopy(payload))
    if canonical_json(first) != canonical_json(second):
        return False, "adapter returned different results for identical isolated fixtures"
    return True, None
