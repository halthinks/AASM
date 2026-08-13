from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
import json
from typing import Any, Iterable, Mapping

from .profile_packages import canonical_hash


SEMANTIC_CLASSIFICATIONS = {
    "PASS",
    "LOCAL_DEFECT",
    "INFORMATION_GAP",
    "ASSUMPTION_CONFLICT",
    "EVIDENCE_CONFLICT",
    "POLICY_CONFLICT",
    "FATAL",
}
CONFLICT_CLASSIFICATIONS = {
    "ASSUMPTION_CONFLICT",
    "EVIDENCE_CONFLICT",
    "POLICY_CONFLICT",
}
PRODUCER_TYPES = {"adapter", "agent", "human", "service", "simulator", "tool", "validator", "other"}

DOMAIN_CONTRACT_ID = "aasm.domain.v1"
DOMAIN_CONTRACT_VERSION = "0.1.0"
PROBLEM_CONTRACT_ID = "aasm.problem.v1"
PROBLEM_CONTRACT_VERSION = "0.1.0"
SEMANTIC_PROBLEM_CONTRACT_ID = "aasm.semantic.problem.v1"
SEMANTIC_PROBLEM_CONTRACT_VERSION = "0.1.0"
COMPILE_STATUSES = {
    "UNCOMPILED",
    "PARTIALLY_SPECIFIED",
    "WELL_FORMED",
    "SOLVABLE",
    "BLOCKED_MISSING_INPUTS",
    "BLOCKED_MISSING_CAPABILITIES",
    "CONTRADICTORY",
    "EXECUTING",
    "COMPLETE",
    "FAILED",
}


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    raise TypeError(f"semantic value is not JSON serializable: {type(value)!r}")


def canonical_semantic_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_fingerprint(value: Any) -> str:
    return canonical_hash(_jsonable(value))


def _unique_ids(rows: Iterable[Any], attr: str) -> list[str]:
    ids = [str(getattr(row, attr) if not isinstance(row, Mapping) else row[attr]) for row in rows]
    return ids


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for value in values:
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return sorted(duplicate)


def _predicate_ref(row: Any) -> str | None:
    if isinstance(row, Mapping):
        value = row.get("predicate_id") or row.get("predicate")
        return None if value is None else str(value)
    return None


def _fact_key(row: Mapping[str, Any]) -> tuple[str, str]:
    predicate = str(row.get("predicate_id") or row.get("predicate") or "")
    arguments = canonical_semantic_json(row.get("arguments") or row.get("args") or [])
    return predicate, arguments


@dataclass
class ProducerRef:
    producer_type: str
    producer_id: str
    version: str = ""
    authority: str = "UNSPECIFIED"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.producer_type not in PRODUCER_TYPES:
            raise ValueError(f"invalid producer_type: {self.producer_type}")
        if not self.producer_id:
            raise ValueError("producer_id is required")

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProducerRef":
        payload = deepcopy(data)
        if "type" in payload and "producer_type" not in payload: payload["producer_type"] = payload.pop("type")
        if "id" in payload and "producer_id" not in payload: payload["producer_id"] = payload.pop("id")
        return cls(**payload)


@dataclass
class SemanticResultEnvelope:
    result_id: str
    producer: ProducerRef
    subject_ids: list[str]
    classification: str
    summary: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    proposed_conflict: dict[str, Any] | None = None
    confidence: float | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        if not self.result_id or not self.summary.strip(): raise ValueError("result_id and summary are required")
        if not isinstance(self.producer, ProducerRef): self.producer = ProducerRef.from_dict(self.producer)
        self.subject_ids = sorted(set(str(value) for value in self.subject_ids))
        if not self.subject_ids: raise ValueError("semantic result requires at least one subject_id")
        if self.classification not in SEMANTIC_CLASSIFICATIONS: raise ValueError(f"invalid semantic-result classification: {self.classification}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0: raise ValueError("confidence must be between 0 and 1")
        if self.schema_version != 1: raise ValueError("unsupported semantic-result schema_version")
        if self.classification in CONFLICT_CLASSIFICATIONS and not (self.proposed_conflict or self.evidence or self.observations):
            raise ValueError("conflict-classified semantic result requires a proposed conflict, evidence, or observations")
        try: json.dumps(self.to_dict(), sort_keys=True, default=None)
        except (TypeError, ValueError) as exc: raise ValueError(f"semantic result is not JSON serializable: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self); out["producer"] = self.producer.to_dict(); return out

    @property
    def fingerprint(self) -> str: return canonical_hash(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticResultEnvelope":
        payload = deepcopy(data); payload["producer"] = ProducerRef.from_dict(payload["producer"]); return cls(**payload)


@dataclass(frozen=True)
class Entity:
    entity_id: str
    kind: str
    attributes: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.entity_id or not self.kind: raise ValueError("entity_id and kind are required")
        _jsonable(self.attributes)
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class Predicate:
    predicate_id: str
    arity: int = 0
    argument_kinds: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.predicate_id: raise ValueError("predicate_id is required")
        if self.arity < 0: raise ValueError("predicate arity must be non-negative")
        if self.argument_kinds and len(self.argument_kinds) != self.arity: raise ValueError("argument_kinds length must equal arity")
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class Objective:
    objective_id: str
    predicate_id: str
    direction: str = "SATISFY"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.objective_id or not self.predicate_id: raise ValueError("objective_id and predicate_id are required")
        if self.direction not in {"SATISFY", "MINIMIZE", "MAXIMIZE"}: raise ValueError("invalid objective direction")
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class Operator:
    operator_id: str
    required_capabilities: tuple[str, ...] = ()
    preconditions: tuple[dict[str, Any], ...] = ()
    effects: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.operator_id: raise ValueError("operator_id is required")
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class Observer:
    observer_id: str
    required_capabilities: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.observer_id: raise ValueError("observer_id is required")
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class Verifier:
    verifier_id: str
    required_capabilities: tuple[str, ...] = ()
    accepts: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.verifier_id: raise ValueError("verifier_id is required")
    def to_dict(self) -> dict[str, Any]: return _jsonable(asdict(self))


@dataclass(frozen=True)
class DomainPackage:
    package_id: str
    version: str
    type_registry: dict[str, Any] = field(default_factory=dict)
    predicate_registry: tuple[str, ...] = ()
    relation_registry: tuple[str, ...] = ()
    decision_variable_kinds: tuple[str, ...] = ()
    operators: tuple[Operator, ...] = ()
    observers: tuple[Observer, ...] = ()
    verifiers: tuple[Verifier, ...] = ()
    conflict_rules: tuple[dict[str, Any], ...] = ()
    projection_policy: dict[str, Any] = field(default_factory=dict)
    objective_policy: dict[str, Any] = field(default_factory=dict)
    completion_templates: tuple[dict[str, Any], ...] = ()
    authority_policy: dict[str, Any] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    contract: str = DOMAIN_CONTRACT_ID

    def __post_init__(self):
        if not self.package_id or not self.version: raise ValueError("package_id and version are required")
        if self.contract != DOMAIN_CONTRACT_ID: raise ValueError(f"unsupported domain contract: {self.contract}")
        object.__setattr__(self, "operators", tuple(item if isinstance(item, Operator) else Operator(**item) for item in self.operators))
        object.__setattr__(self, "observers", tuple(item if isinstance(item, Observer) else Observer(**item) for item in self.observers))
        object.__setattr__(self, "verifiers", tuple(item if isinstance(item, Verifier) else Verifier(**item) for item in self.verifiers))
        if _duplicates(_unique_ids(self.operators, "operator_id")): raise ValueError("duplicate operator_id")
        if _duplicates(_unique_ids(self.observers, "observer_id")): raise ValueError("duplicate observer_id")
        if _duplicates(_unique_ids(self.verifiers, "verifier_id")): raise ValueError("duplicate verifier_id")

    def payload(self) -> dict[str, Any]:
        return {key: value for key, value in _jsonable(asdict(self)).items() if key != "fingerprint"}

    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.payload())

    def to_dict(self) -> dict[str, Any]:
        out = self.payload(); out["fingerprint"] = self.fingerprint; return out


@dataclass(frozen=True)
class ProblemDefinition:
    definition_id: str
    version: str
    goal: dict[str, Any]
    required_entity_kinds: tuple[str, ...] = ()
    required_predicates: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.definition_id or not self.version: raise ValueError("definition_id and version are required")
        if not self.goal: raise ValueError("problem definition goal is required")
    def to_dict(self) -> dict[str, Any]:
        out = _jsonable(asdict(self)); out["fingerprint"] = semantic_fingerprint(out); return out


@dataclass(frozen=True)
class ProblemModel:
    model_id: str
    version: str
    entities: tuple[Entity, ...] = ()
    predicates: tuple[Predicate, ...] = ()
    operators: tuple[Operator, ...] = ()
    observers: tuple[Observer, ...] = ()
    verifiers: tuple[Verifier, ...] = ()
    objectives: tuple[Objective, ...] = ()
    constraints: tuple[dict[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.model_id or not self.version: raise ValueError("model_id and version are required")
        object.__setattr__(self, "entities", tuple(item if isinstance(item, Entity) else Entity(**item) for item in self.entities))
        object.__setattr__(self, "predicates", tuple(item if isinstance(item, Predicate) else Predicate(**item) for item in self.predicates))
        object.__setattr__(self, "operators", tuple(item if isinstance(item, Operator) else Operator(**item) for item in self.operators))
        object.__setattr__(self, "observers", tuple(item if isinstance(item, Observer) else Observer(**item) for item in self.observers))
        object.__setattr__(self, "verifiers", tuple(item if isinstance(item, Verifier) else Verifier(**item) for item in self.verifiers))
        object.__setattr__(self, "objectives", tuple(item if isinstance(item, Objective) else Objective(**item) for item in self.objectives))
        duplicate_groups = {
            "entity_id": _duplicates(_unique_ids(self.entities, "entity_id")),
            "predicate_id": _duplicates(_unique_ids(self.predicates, "predicate_id")),
            "operator_id": _duplicates(_unique_ids(self.operators, "operator_id")),
            "observer_id": _duplicates(_unique_ids(self.observers, "observer_id")),
            "verifier_id": _duplicates(_unique_ids(self.verifiers, "verifier_id")),
            "objective_id": _duplicates(_unique_ids(self.objectives, "objective_id")),
        }
        bad = {key: value for key, value in duplicate_groups.items() if value}
        if bad: raise ValueError(f"duplicate semantic IDs: {bad}")

    @property
    def fingerprint(self) -> str: return semantic_fingerprint(_jsonable(asdict(self)))
    def to_dict(self) -> dict[str, Any]:
        out = _jsonable(asdict(self)); out["fingerprint"] = self.fingerprint; return out


@dataclass(frozen=True)
class ProblemInstance:
    instance_id: str
    domain_package_id: str
    domain_package_fingerprint: str
    definition_id: str
    definition_fingerprint: str
    model_id: str
    model_fingerprint: str
    goal: dict[str, Any]
    universe: tuple[str, ...] = ()
    decision_variables: dict[str, Any] = field(default_factory=dict)
    facts: tuple[dict[str, Any], ...] = ()
    assumptions: tuple[dict[str, Any], ...] = ()
    obligations: tuple[dict[str, Any], ...] = ()
    constraints: tuple[dict[str, Any], ...] = ()
    objectives: tuple[dict[str, Any], ...] = ()
    capability_bindings: dict[str, Any] = field(default_factory=dict)
    completion_rule: dict[str, Any] = field(default_factory=dict)
    compile_status: str = "UNCOMPILED"
    unresolved_specification: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    contract: str = PROBLEM_CONTRACT_ID

    def __post_init__(self):
        if not self.instance_id or not self.domain_package_id: raise ValueError("instance_id and domain_package_id are required")
        if self.contract != PROBLEM_CONTRACT_ID: raise ValueError(f"unsupported problem contract: {self.contract}")
        if self.compile_status not in COMPILE_STATUSES: raise ValueError(f"invalid compile_status: {self.compile_status}")
        if not self.goal: raise ValueError("problem instance goal is required")

    def payload(self) -> dict[str, Any]: return _jsonable(asdict(self))
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.payload())
    def to_dict(self) -> dict[str, Any]:
        out = self.payload(); out["fingerprint"] = self.fingerprint; return out



def semantic_problem_contract() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_PROBLEM_CONTRACT_ID,
        "contract_version": SEMANTIC_PROBLEM_CONTRACT_VERSION,
        "schema_version": 1,
        "domain_contract": DOMAIN_CONTRACT_ID,
        "problem_contract": PROBLEM_CONTRACT_ID,
        "authority": "AASM_EVENT_REDUCER_ONLY",
        "serialization": "CANONICAL_JSON_SHA256",
        "compile_statuses": sorted(COMPILE_STATUSES),
        "objects": ["DomainPackage", "ProblemDefinition", "ProblemModel", "ProblemInstance", "Entity", "Predicate", "Objective", "Operator", "Observer", "Verifier"],
    }


def validate_problem_model(domain: DomainPackage, definition: ProblemDefinition, model: ProblemModel) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    predicate_ids = {row.predicate_id for row in model.predicates}
    entity_kinds = {row.kind for row in model.entities}
    for required in definition.required_entity_kinds:
        if required not in entity_kinds: errors.append(f"missing required entity kind: {required}")
    for required in definition.required_predicates:
        if required not in predicate_ids: errors.append(f"missing required predicate: {required}")
    for objective in model.objectives:
        if objective.predicate_id not in predicate_ids: errors.append(f"objective {objective.objective_id} references unknown predicate {objective.predicate_id}")
    for operator in model.operators:
        for row in [*operator.preconditions, *operator.effects]:
            predicate_id = _predicate_ref(row)
            if predicate_id and predicate_id not in predicate_ids: errors.append(f"operator {operator.operator_id} references unknown predicate {predicate_id}")
    domain_predicates = set(domain.predicate_registry)
    if domain_predicates:
        unknown = sorted(predicate_ids - domain_predicates)
        if unknown: errors.append(f"model predicates are not registered by domain: {unknown}")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "domain_fingerprint": domain.fingerprint, "definition_fingerprint": definition.to_dict()["fingerprint"],
            "model_fingerprint": model.fingerprint}


def build_problem_instance(
    domain: DomainPackage,
    definition: ProblemDefinition,
    model: ProblemModel,
    *,
    instance_id: str,
    decision_variables: dict[str, Any] | None = None,
    facts: Iterable[dict[str, Any]] = (),
    assumptions: Iterable[dict[str, Any]] = (),
    obligations: Iterable[dict[str, Any]] = (),
    constraints: Iterable[dict[str, Any]] = (),
    capability_bindings: dict[str, Any] | None = None,
    completion_rule: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProblemInstance:
    model_report = validate_problem_model(domain, definition, model)
    facts_tuple = tuple(deepcopy(list(facts)))
    assumptions_tuple = tuple(deepcopy(list(assumptions)))
    decision_variables = deepcopy(decision_variables or {})
    capability_bindings = deepcopy(capability_bindings or {})
    errors = list(model_report["errors"])
    unresolved: list[str] = []
    predicate_ids = {row.predicate_id for row in model.predicates}
    for row in [*facts_tuple, *assumptions_tuple]:
        predicate_id = _predicate_ref(row)
        if predicate_id and predicate_id not in predicate_ids: errors.append(f"fact/assumption references unknown predicate {predicate_id}")
    for variable_id, raw in decision_variables.items():
        if not isinstance(raw, Mapping):
            errors.append(f"decision variable {variable_id} must be an object"); continue
        domain_values = list(raw.get("domain") or [])
        if not domain_values: errors.append(f"decision variable {variable_id} has empty domain")
        if "value" in raw and raw["value"] not in domain_values: errors.append(f"decision variable {variable_id} value is outside domain")
    known: dict[tuple[str, str], Any] = {}
    contradictory = False
    for row in [*facts_tuple, *assumptions_tuple]:
        key = _fact_key(row)
        if not key[0]: continue
        value = row.get("value", True)
        if key in known and known[key] != value:
            contradictory = True
            errors.append(f"hard contradiction for predicate {key[0]} arguments {key[1]}")
        known[key] = value
    required_capabilities = set(domain.required_capabilities)
    for item in [*model.operators, *model.observers, *model.verifiers]: required_capabilities.update(item.required_capabilities)
    missing_capabilities = sorted(capability for capability in required_capabilities if capability not in capability_bindings)
    if missing_capabilities: unresolved.extend(f"capability:{item}" for item in missing_capabilities)
    if contradictory: status = "CONTRADICTORY"
    elif errors: status = "PARTIALLY_SPECIFIED"
    elif missing_capabilities: status = "BLOCKED_MISSING_CAPABILITIES"
    else: status = "SOLVABLE"
    instance = ProblemInstance(
        instance_id=instance_id,
        domain_package_id=domain.package_id,
        domain_package_fingerprint=domain.fingerprint,
        definition_id=definition.definition_id,
        definition_fingerprint=definition.to_dict()["fingerprint"],
        model_id=model.model_id,
        model_fingerprint=model.fingerprint,
        goal=deepcopy(definition.goal),
        universe=tuple(row.entity_id for row in model.entities),
        decision_variables=decision_variables,
        facts=facts_tuple,
        assumptions=assumptions_tuple,
        obligations=tuple(deepcopy(list(obligations))),
        constraints=tuple([*deepcopy(list(model.constraints)), *deepcopy(list(constraints))]),
        objectives=tuple(row.to_dict() for row in model.objectives),
        capability_bindings=capability_bindings,
        completion_rule=deepcopy(completion_rule or {}),
        compile_status=status,
        unresolved_specification=tuple(unresolved),
        metadata={**deepcopy(metadata or {}), "validation_errors": errors},
    )
    return instance


def validate_problem_instance(domain: DomainPackage, definition: ProblemDefinition, model: ProblemModel, instance: ProblemInstance) -> dict[str, Any]:
    errors: list[str] = []
    if instance.domain_package_id != domain.package_id or instance.domain_package_fingerprint != domain.fingerprint: errors.append("domain package identity/fingerprint mismatch")
    if instance.definition_id != definition.definition_id or instance.definition_fingerprint != definition.to_dict()["fingerprint"]: errors.append("problem definition identity/fingerprint mismatch")
    if instance.model_id != model.model_id or instance.model_fingerprint != model.fingerprint: errors.append("problem model identity/fingerprint mismatch")
    errors.extend(validate_problem_model(domain, definition, model)["errors"])
    errors.extend(str(item) for item in (instance.metadata.get("validation_errors") or []))
    if instance.compile_status in {"PARTIALLY_SPECIFIED", "CONTRADICTORY", "FAILED"}: errors.append(f"problem instance compile status blocks admission: {instance.compile_status}")
    return {"valid": not errors, "errors": sorted(set(errors)), "fingerprint": instance.fingerprint, "compile_status": instance.compile_status,
            "unresolved_specification": list(instance.unresolved_specification)}


def semantic_problem_document(domain: DomainPackage, definition: ProblemDefinition, model: ProblemModel, instance: ProblemInstance) -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_PROBLEM_CONTRACT_ID,
        "contract_version": SEMANTIC_PROBLEM_CONTRACT_VERSION,
        "domain_package": domain.to_dict(),
        "problem_definition": definition.to_dict(),
        "problem_model": model.to_dict(),
        "problem_instance": instance.to_dict(),
    }


def semantic_problem_from_document(document: Mapping[str, Any]) -> tuple[DomainPackage, ProblemDefinition, ProblemModel, ProblemInstance]:
    raw_domain = deepcopy(document["domain_package"]); raw_domain.pop("fingerprint", None)
    raw_definition = deepcopy(document["problem_definition"]); raw_definition.pop("fingerprint", None)
    raw_model = deepcopy(document["problem_model"]); raw_model.pop("fingerprint", None)
    raw_instance = deepcopy(document["problem_instance"]); raw_instance.pop("fingerprint", None)
    return DomainPackage(**raw_domain), ProblemDefinition(**raw_definition), ProblemModel(**raw_model), ProblemInstance(**raw_instance)


def validate_semantic_result(data: SemanticResultEnvelope | dict[str, Any]) -> SemanticResultEnvelope:
    return data if isinstance(data, SemanticResultEnvelope) else SemanticResultEnvelope.from_dict(data)


__all__ = [
    "SEMANTIC_CLASSIFICATIONS", "CONFLICT_CLASSIFICATIONS", "PRODUCER_TYPES", "ProducerRef", "SemanticResultEnvelope", "validate_semantic_result",
    "DOMAIN_CONTRACT_ID", "DOMAIN_CONTRACT_VERSION", "PROBLEM_CONTRACT_ID", "PROBLEM_CONTRACT_VERSION",
    "SEMANTIC_PROBLEM_CONTRACT_ID", "SEMANTIC_PROBLEM_CONTRACT_VERSION", "COMPILE_STATUSES",
    "Entity", "Predicate", "Objective", "Operator", "Observer", "Verifier", "DomainPackage", "ProblemDefinition", "ProblemModel", "ProblemInstance",
    "canonical_semantic_json", "semantic_fingerprint", "semantic_problem_contract", "validate_problem_model", "build_problem_instance",
    "validate_problem_instance", "semantic_problem_document", "semantic_problem_from_document",
]