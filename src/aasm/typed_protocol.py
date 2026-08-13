from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .semantic_result import canonical_semantic_json, semantic_fingerprint


TYPED_PROTOCOL_CONTRACT_ID = "aasm.typed.protocol.v1"
TYPED_PROTOCOL_CONTRACT_VERSION = "0.1.0"
CAPABILITY_ABI_CONTRACT_ID = "aasm.capability.abi.v1"
CAPABILITY_ABI_CONTRACT_VERSION = "0.1.0"
FORMAL_STATEMENT_CONTRACT_ID = "aasm.formal.statement.v1"
FORMAL_STATEMENT_CONTRACT_VERSION = "0.1.0"
FORMAL_VERIFICATION_CONTRACT_ID = "aasm.formal.verification.v1"
FORMAL_VERIFICATION_CONTRACT_VERSION = "0.1.0"

CAPABILITY_TYPES = ("OPERATOR", "OBSERVER", "VERIFIER", "HANDLER")
FORMAL_LOGICS = ("tptp", "smtlib2", "lean4", "hol")
FORMAL_QUERY_MODES = ("VALIDITY", "SATISFIABILITY", "COUNTERMODEL", "EQUIVALENCE", "INVARIANT")
FORMAL_RESULT_STATUSES = ("PROVED", "DISPROVED", "SAT", "UNSAT", "COUNTERMODEL", "UNKNOWN", "TIMEOUT", "ERROR")
VERIFICATION_STRENGTHS = ("SOLVER_VERDICT", "MULTI_SOLVER_AGREEMENT", "CHECKED_CERTIFICATE", "TRUSTED_KERNEL")
DISAGREEMENT_POLICIES = ("INCONCLUSIVE", "FAIL_CLOSED")

_SZS_RE = re.compile(r"\bSZS\s+status\s+([A-Za-z][A-Za-z0-9_-]*)\b", re.IGNORECASE)


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
    raise TypeError(f"typed capability value is not JSON serializable: {type(value)!r}")


def _uniq(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values}))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_nonempty(value: str, name: str) -> None:
    if not str(value).strip():
        raise ValueError(f"{name} is required")


def validate_json_payload(schema: Mapping[str, Any], payload: Any, *, path: str = "$") -> None:
    """Deterministic dependency-free validator for the v0.39 protocol subset of JSON Schema."""
    schema = dict(schema or {})
    if not schema:
        return
    if "const" in schema and payload != schema["const"]:
        raise ValueError(f"{path}: value does not match const")
    if "enum" in schema and payload not in schema["enum"]:
        raise ValueError(f"{path}: value is not in enum")
    expected = schema.get("type")
    if expected:
        allowed = (expected,) if isinstance(expected, str) else tuple(expected)
        ok = False
        for kind in allowed:
            if kind == "object" and isinstance(payload, dict): ok = True
            elif kind == "array" and isinstance(payload, list): ok = True
            elif kind == "string" and isinstance(payload, str): ok = True
            elif kind == "integer" and isinstance(payload, int) and not isinstance(payload, bool): ok = True
            elif kind == "number" and isinstance(payload, (int, float)) and not isinstance(payload, bool): ok = True
            elif kind == "boolean" and isinstance(payload, bool): ok = True
            elif kind == "null" and payload is None: ok = True
        if not ok:
            raise ValueError(f"{path}: expected JSON type {allowed}")
    if isinstance(payload, dict):
        required = tuple(str(value) for value in schema.get("required", ()))
        missing = sorted(set(required) - set(payload))
        if missing:
            raise ValueError(f"{path}: missing required properties {missing}")
        properties = schema.get("properties") or {}
        if schema.get("additionalProperties", True) is False:
            unknown = sorted(set(payload) - set(properties))
            if unknown:
                raise ValueError(f"{path}: unknown properties {unknown}")
        for key, subschema in properties.items():
            if key in payload:
                validate_json_payload(subschema, payload[key], path=f"{path}.{key}")
    if isinstance(payload, list) and "items" in schema:
        for index, item in enumerate(payload):
            validate_json_payload(schema["items"], item, path=f"{path}[{index}]")
    if isinstance(payload, str):
        if "minLength" in schema and len(payload) < int(schema["minLength"]): raise ValueError(f"{path}: string shorter than minLength")
        if "maxLength" in schema and len(payload) > int(schema["maxLength"]): raise ValueError(f"{path}: string longer than maxLength")
        if "pattern" in schema and re.search(str(schema["pattern"]), payload) is None: raise ValueError(f"{path}: string does not match pattern")
    if isinstance(payload, (int, float)) and not isinstance(payload, bool):
        if "minimum" in schema and payload < schema["minimum"]: raise ValueError(f"{path}: value below minimum")
        if "maximum" in schema and payload > schema["maximum"]: raise ValueError(f"{path}: value above maximum")


@dataclass(frozen=True)
class TypedEventSchema:
    name: str
    payload_schema: dict[str, Any]
    required_evidence_types: tuple[str, ...] = ()
    guards: tuple[str, ...] = ()
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_id: str = ""

    def __post_init__(self):
        _require_nonempty(self.name, "typed event name"); _require_nonempty(self.version, "typed event version")
        object.__setattr__(self, "required_evidence_types", _uniq(self.required_evidence_types)); object.__setattr__(self, "guards", _uniq(self.guards))
        _jsonable(self.payload_schema); _jsonable(self.metadata)
        if not self.schema_id: object.__setattr__(self, "schema_id", f"typed-event-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {"name": self.name, "payload_schema": _jsonable(self.payload_schema), "required_evidence_types": list(self.required_evidence_types), "guards": list(self.guards), "version": self.version, "metadata": _jsonable(self.metadata)}

    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"schema_id": self.schema_id, **self.identity_payload()})
    def validate(self, payload: Any) -> None: validate_json_payload(self.payload_schema, payload)
    def to_dict(self) -> dict[str, Any]: return {"schema_id": self.schema_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TypedEventSchema":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ScopedLegalTransition:
    from_state: str
    event: str
    to_state: str
    decision_name: str
    obligations_created: tuple[str, ...] = ()
    evidence_required: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    transition_id: str = ""

    def __post_init__(self):
        for name, value in (("from_state", self.from_state), ("event", self.event), ("to_state", self.to_state), ("decision_name", self.decision_name)): _require_nonempty(value, name)
        object.__setattr__(self, "obligations_created", _uniq(self.obligations_created)); object.__setattr__(self, "evidence_required", _uniq(self.evidence_required)); _jsonable(self.metadata)
        if not self.transition_id: object.__setattr__(self, "transition_id", f"typed-transition-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {"from_state": self.from_state, "event": self.event, "to_state": self.to_state, "decision_name": self.decision_name, "obligations_created": list(self.obligations_created), "evidence_required": list(self.evidence_required), "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"transition_id": self.transition_id, **self.identity_payload()})
    def to_dict(self) -> dict[str, Any]: return {"transition_id": self.transition_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ScopedLegalTransition":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class PatternMachine:
    name: str
    version: str
    scope_id: str
    states: tuple[str, ...]
    initial_state: str
    transitions: tuple[ScopedLegalTransition | dict[str, Any], ...]
    event_vocabulary: tuple[TypedEventSchema | dict[str, Any], ...]
    metadata: dict[str, Any] = field(default_factory=dict)
    pattern_id: str = ""

    def __post_init__(self):
        _require_nonempty(self.name, "pattern name"); _require_nonempty(self.version, "pattern version"); _require_nonempty(self.scope_id, "scope_id")
        states = _uniq(self.states)
        if not states: raise ValueError("pattern requires states")
        if self.initial_state not in states: raise ValueError("pattern initial_state must be one of states")
        transitions = tuple(item if isinstance(item, ScopedLegalTransition) else ScopedLegalTransition.from_dict(item) for item in self.transitions)
        events = tuple(item if isinstance(item, TypedEventSchema) else TypedEventSchema.from_dict(item) for item in self.event_vocabulary)
        event_names = [row.name for row in events]
        if len(event_names) != len(set(event_names)): raise ValueError("pattern event vocabulary names must be unique")
        event_set, state_set, seen_pairs = set(event_names), set(states), set()
        for transition in transitions:
            if transition.from_state not in state_set or transition.to_state not in state_set: raise ValueError("pattern transition references unknown state")
            if transition.event not in event_set: raise ValueError("pattern transition references unknown event schema")
            pair = (transition.from_state, transition.event)
            if pair in seen_pairs: raise ValueError("pattern transitions must be deterministic for each state/event pair")
            seen_pairs.add(pair)
        object.__setattr__(self, "states", states); object.__setattr__(self, "transitions", tuple(sorted(transitions, key=lambda row: row.transition_id))); object.__setattr__(self, "event_vocabulary", tuple(sorted(events, key=lambda row: row.name))); _jsonable(self.metadata)
        if not self.pattern_id: object.__setattr__(self, "pattern_id", f"pattern-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version, "scope_id": self.scope_id, "states": list(self.states), "initial_state": self.initial_state, "transitions": [row.to_dict() for row in self.transitions], "event_vocabulary": [row.to_dict() for row in self.event_vocabulary], "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self) -> str: return semantic_fingerprint({"pattern_id": self.pattern_id, **self.identity_payload()})
    def event_schema(self, name: str) -> TypedEventSchema:
        for row in self.event_vocabulary:
            if row.name == name: return row
        raise KeyError(name)
    def transition_for(self, state: str, event: str) -> ScopedLegalTransition:
        matches = [row for row in self.transitions if row.from_state == state and row.event == event]
        if not matches: raise ValueError(f"illegal typed transition: {state} + {event}")
        return matches[0]
    def to_dict(self) -> dict[str, Any]: return {"pattern_id": self.pattern_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PatternMachine":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    capability_type: str
    version: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    supported_logics: tuple[str, ...] = ()
    query_modes: tuple[str, ...] = ()
    evidence_types: tuple[str, ...] = ()
    deterministic: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _require_nonempty(self.capability_id, "capability_id"); _require_nonempty(self.version, "capability version")
        if self.capability_type not in CAPABILITY_TYPES: raise ValueError(f"invalid capability type: {self.capability_type}")
        logics, modes = _uniq(self.supported_logics), _uniq(self.query_modes)
        if any(value not in FORMAL_LOGICS for value in logics): raise ValueError("capability supported_logics contains unsupported logic")
        if any(value not in FORMAL_QUERY_MODES for value in modes): raise ValueError("capability query_modes contains unsupported mode")
        object.__setattr__(self, "supported_logics", logics); object.__setattr__(self, "query_modes", modes); object.__setattr__(self, "evidence_types", _uniq(self.evidence_types)); _jsonable(self.input_schema); _jsonable(self.output_schema); _jsonable(self.metadata)
    @property
    def token(self) -> str: return f"aasm.capability:{self.capability_id}@{self.version}"
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.payload())
    def payload(self) -> dict[str, Any]: return _jsonable(asdict(self))
    def to_dict(self) -> dict[str, Any]: return {**self.payload(), "token": self.token, "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CapabilityContract":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); payload.pop("token", None); return cls(**payload)


@dataclass(frozen=True)
class CapabilityProvider:
    provider_id: str
    capability_id: str
    capability_version: str
    resource_id: str
    implementation: str
    supported_logics: tuple[str, ...] = ()
    query_modes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for name, value in (("provider_id", self.provider_id), ("capability_id", self.capability_id), ("capability_version", self.capability_version), ("resource_id", self.resource_id), ("implementation", self.implementation)): _require_nonempty(value, name)
        object.__setattr__(self, "supported_logics", _uniq(self.supported_logics)); object.__setattr__(self, "query_modes", _uniq(self.query_modes)); _jsonable(self.metadata)
    @property
    def capability_token(self) -> str: return f"aasm.capability:{self.capability_id}@{self.capability_version}"
    @property
    def provider_token(self) -> str: return f"aasm.provider:{self.provider_id}"
    @property
    def fingerprint(self) -> str: return semantic_fingerprint(self.payload())
    def payload(self) -> dict[str, Any]: return _jsonable(asdict(self))
    def to_dict(self) -> dict[str, Any]: return {**self.payload(), "capability_token": self.capability_token, "provider_token": self.provider_token, "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CapabilityProvider":
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); payload.pop("capability_token", None); payload.pop("provider_token", None); return cls(**payload)


__all__ = [
    "TYPED_PROTOCOL_CONTRACT_ID", "TYPED_PROTOCOL_CONTRACT_VERSION", "CAPABILITY_ABI_CONTRACT_ID", "CAPABILITY_ABI_CONTRACT_VERSION",
    "FORMAL_STATEMENT_CONTRACT_ID", "FORMAL_STATEMENT_CONTRACT_VERSION", "FORMAL_VERIFICATION_CONTRACT_ID", "FORMAL_VERIFICATION_CONTRACT_VERSION",
    "CAPABILITY_TYPES", "FORMAL_LOGICS", "FORMAL_QUERY_MODES", "FORMAL_RESULT_STATUSES", "VERIFICATION_STRENGTHS", "DISAGREEMENT_POLICIES",
    "TypedEventSchema", "ScopedLegalTransition", "PatternMachine", "CapabilityContract", "CapabilityProvider", "validate_json_payload",
]
