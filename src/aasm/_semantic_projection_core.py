from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence
from .semantic_result import semantic_fingerprint

SEMANTIC_PROJECTION_CONTRACT_ID = "aasm.semantic.projection.v1"
SEMANTIC_PROJECTION_CONTRACT_VERSION = "0.1.0"
SEMANTIC_EQUIVALENCE_CONTRACT_ID = "aasm.semantic.equivalence.v1"
SEMANTIC_EQUIVALENCE_CONTRACT_VERSION = "0.1.0"
INVARIANT_CONTRACT_ID = "aasm.invariant.v1"
INVARIANT_CONTRACT_VERSION = "0.1.0"
SEMANTIC_PROJECTION_STABILITY = "FOUNDATION_EXPERIMENTAL"
INVARIANT_CLASSIFICATIONS = ("REPRESENTATIONAL", "STATIC_PROTOCOL", "DYNAMIC_KERNEL", "EMPIRICAL")
INVARIANT_TREATMENTS = ("PRESERVED", "DISCARDED", "UNSUPPORTED")
PROJECTION_FIDELITIES = ("LOSSLESS", "LOSSY")
PROJECTION_STATUSES = ("PROJECTED", "UNSUPPORTED", "INDETERMINATE")
REVISION_POLICIES = ("EXACT_MATCH_REQUIRED", "EXPLICIT_CROSS_REVISION")
EQUIVALENCE_RELATIONS = ("EXACT_IDENTITY", "PROJECTION_EQUIVALENT", "NON_EQUIVALENT", "INDETERMINATE", "UNSUPPORTED")
REVISION_RELATIONS = ("SAME", "DIFFERENT", "UNBOUND")
_SHA = re.compile(r"^[0-9a-f]{64}$")

def _req(name: str, value: Any) -> str:
    value = str(value).strip()
    if not value: raise ValueError(f"semantic projection {name} is required")
    return value

def _opt(value: Any) -> str: return "" if value is None else str(value).strip()
def _sha(name: str, value: Any) -> str:
    value = _req(name, value).lower()
    if not _SHA.fullmatch(value): raise ValueError(f"semantic projection {name} must be a lowercase 64-hex SHA-256 digest")
    return value

def _uniq(values: Sequence[Any]) -> tuple[str, ...]: return tuple(sorted({_req("list value", v) for v in values}))
def _jsonable(value: Any) -> Any:
    if hasattr(value, "identity_payload"): return _jsonable(value.identity_payload())
    if hasattr(value, "to_dict"): return _jsonable(value.to_dict())
    if isinstance(value, Mapping): return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))}
    if isinstance(value, (tuple, list, set)): return [_jsonable(v) for v in value]
    if isinstance(value, float): raise TypeError("binary floating-point values are forbidden in semantic projection portable identity")
    if isinstance(value, (str, int, bool)) or value is None: return value
    raise TypeError(f"semantic projection value is not JSON serializable: {type(value)!r}")

def _roundtrip(cls, value: Mapping[str, Any], list_fields: Sequence[str] = ()):
    payload = deepcopy(dict(value)); payload.pop("record_type", None); supplied = str(payload.pop("fingerprint", "")).strip()
    for name in list_fields: payload[name] = tuple(payload.get(name) or ())
    item = cls(**payload)
    if supplied and supplied != item.fingerprint:
        label = "result" if cls.__name__.endswith("Result") else "assessment" if cls.__name__.endswith("Assessment") else cls.__name__
        raise ValueError(f"semantic {label} fingerprint mismatch")
    return item

@dataclass(frozen=True)
class InvariantRef:
    invariant_id: str
    classification: str
    treatment: str = "PRESERVED"
    def __post_init__(self):
        iid = _req("invariant_id", self.invariant_id); c = _req("invariant classification", self.classification).upper(); t = _req("invariant treatment", self.treatment).upper()
        if c not in INVARIANT_CLASSIFICATIONS: raise ValueError(f"unsupported invariant classification: {c}")
        if t not in INVARIANT_TREATMENTS: raise ValueError(f"unsupported invariant treatment: {t}")
        object.__setattr__(self, "invariant_id", iid); object.__setattr__(self, "classification", c); object.__setattr__(self, "treatment", t)
    def identity_payload(self): return {"invariant_id": self.invariant_id, "classification": self.classification, "treatment": self.treatment}
    def to_dict(self): return self.identity_payload()
    @classmethod
    def from_dict(cls, v): return cls(str(v["invariant_id"]), str(v["classification"]), str(v.get("treatment") or "PRESERVED"))

@dataclass(frozen=True)
class SemanticSubjectRef:
    semantic_type_id: str
    object_id: str
    fingerprint: str
    revision_id: str = ""
    revision_fingerprint: str = ""
    def __post_init__(self):
        typ = _req("semantic_type_id", self.semantic_type_id); oid = _req("object_id", self.object_id); fp = _sha("subject fingerprint", self.fingerprint)
        rid, rfp = _opt(self.revision_id), _opt(self.revision_fingerprint)
        if bool(rid) != bool(rfp): raise ValueError("semantic projection revision_id and revision_fingerprint must both be present or both be absent")
        if rfp: rfp = _sha("revision_fingerprint", rfp)
        for k, v in (("semantic_type_id", typ), ("object_id", oid), ("fingerprint", fp), ("revision_id", rid), ("revision_fingerprint", rfp)): object.__setattr__(self, k, v)
    @property
    def revision_bound(self): return bool(self.revision_id)
    def identity_payload(self): return {"semantic_type_id": self.semantic_type_id, "object_id": self.object_id, "fingerprint": self.fingerprint, "revision_id": self.revision_id, "revision_fingerprint": self.revision_fingerprint}
    def to_dict(self): return self.identity_payload()
    @classmethod
    def from_dict(cls, v): return cls(str(v["semantic_type_id"]), str(v["object_id"]), str(v["fingerprint"]), str(v.get("revision_id") or ""), str(v.get("revision_fingerprint") or ""))

@dataclass(frozen=True)
class SemanticProjectionDefinition:
    projection_name: str
    source_type_ids: tuple[str, ...]
    target_type_id: str
    purpose: str
    fidelity: str
    invariants: tuple[InvariantRef | Mapping[str, Any], ...]
    discarded_semantics: tuple[str, ...] = ()
    unsupported_semantics: tuple[str, ...] = ()
    revision_policy: str = "EXACT_MATCH_REQUIRED"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    projection_id: str = ""
    contract_id: str = SEMANTIC_PROJECTION_CONTRACT_ID
    contract_version: str = SEMANTIC_PROJECTION_CONTRACT_VERSION
    def __post_init__(self):
        if self.contract_id != SEMANTIC_PROJECTION_CONTRACT_ID or self.contract_version != SEMANTIC_PROJECTION_CONTRACT_VERSION: raise ValueError("unsupported semantic projection contract")
        name = _req("projection_name", self.projection_name); sources = _uniq(self.source_type_ids)
        if not sources: raise ValueError("semantic projection requires at least one source_type_id")
        target, purpose = _req("target_type_id", self.target_type_id), _req("purpose", self.purpose)
        fidelity, policy = _req("fidelity", self.fidelity).upper(), _req("revision_policy", self.revision_policy).upper()
        if fidelity not in PROJECTION_FIDELITIES: raise ValueError(f"unsupported semantic projection fidelity: {fidelity}")
        if policy not in REVISION_POLICIES: raise ValueError(f"unsupported semantic projection revision policy: {policy}")
        inv = tuple(v if isinstance(v, InvariantRef) else InvariantRef.from_dict(v) for v in self.invariants)
        if not inv: raise ValueError("semantic projection requires at least one explicit invariant binding")
        if len({v.invariant_id for v in inv}) != len(inv): raise ValueError("duplicate invariant_id in semantic projection")
        inv = tuple(sorted(inv, key=lambda v: v.invariant_id)); discarded, unsupported = _uniq(self.discarded_semantics), _uniq(self.unsupported_semantics)
        discarded_inv = tuple(v.invariant_id for v in inv if v.treatment == "DISCARDED")
        if fidelity == "LOSSLESS" and (discarded or discarded_inv): raise ValueError("LOSSLESS semantic projection cannot discard declared semantics or invariants")
        if fidelity == "LOSSY" and not (discarded or discarded_inv): raise ValueError("LOSSY semantic projection must explicitly declare discarded semantics or invariants")
        metadata = _jsonable(dict(self.metadata))
        for k, v in (("projection_name", name), ("source_type_ids", sources), ("target_type_id", target), ("purpose", purpose), ("fidelity", fidelity), ("invariants", inv), ("discarded_semantics", discarded), ("unsupported_semantics", unsupported), ("revision_policy", policy), ("metadata", metadata)): object.__setattr__(self, k, v)
        derived = f"semantic-projection-{semantic_fingerprint(self.identity_payload())[:24]}"; supplied = _opt(self.projection_id)
        if supplied and supplied != derived: raise ValueError("semantic projection projection_id does not match canonical identity")
        object.__setattr__(self, "projection_id", derived)
    def identity_payload(self):
        return {"contract_id": self.contract_id, "contract_version": self.contract_version, "projection_name": self.projection_name, "source_type_ids": list(self.source_type_ids), "target_type_id": self.target_type_id, "purpose": self.purpose, "fidelity": self.fidelity, "invariants": [v.identity_payload() for v in self.invariants], "discarded_semantics": list(self.discarded_semantics), "unsupported_semantics": list(self.unsupported_semantics), "revision_policy": self.revision_policy, "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self): return semantic_fingerprint({"projection_id": self.projection_id, **self.identity_payload()})
    def to_dict(self): return {"record_type": "PROJECTION_DEFINITION", "projection_id": self.projection_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, v):
        p = deepcopy(dict(v)); p.pop("record_type", None); supplied = str(p.pop("fingerprint", "")).strip()
        for name in ("source_type_ids", "invariants", "discarded_semantics", "unsupported_semantics"): p[name] = tuple(p.get(name) or ())
        item = cls(**p)
        if supplied and supplied != item.fingerprint: raise ValueError("semantic projection definition fingerprint mismatch")
        return item
