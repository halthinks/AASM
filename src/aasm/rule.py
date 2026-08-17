from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .semantic_evolution import ExternalReference
from .semantic_result import semantic_fingerprint


RULE_CONTRACT_ID = "aasm.rule.v1"
RULE_CONTRACT_VERSION = "0.1.0"
RULE_STABILITY = "FOUNDATION_EXPERIMENTAL"

RULE_STRENGTHS = (
    "HARD_FLOOR",
    "HARD",
    "POLICY",
    "PREFERENCE",
    "ADVISORY",
)
RULE_SEVERITIES = ("INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL")
RULE_SCOPE_MATCH_POLICIES = ("EXACT", "DESCENDANT_OR_SELF", "ANY_IN_WORKSPACE")
RULE_PREDICATE_KINDS = ("ALWAYS", "CONTEXT_MATCH")
RULE_WAIVER_MODES = ("FORBIDDEN", "EXPLICIT_AUTHORIZED")
RULE_OVERRIDE_MODES = (
    "FORBIDDEN",
    "STRICTLY_STRONGER_EXPLICIT",
    "SAME_OR_STRONGER_EXPLICIT",
)
RULE_APPLICABILITY_RESULTS = ("APPLICABLE", "NOT_APPLICABLE", "INDETERMINATE")
RULE_PRECEDENCE_RELATIONS = (
    "LEFT_PRECEDES",
    "RIGHT_PRECEDES",
    "EQUIVALENT_PRECEDENCE",
    "INCOMPARABLE",
)
RULE_CLAUSE_KINDS = (
    "CONSTRAINT",
    "REQUIREMENT",
    "POLICY",
    "VERIFIER_PREDICATE",
    "SAFETY_INVARIANT",
    "OTHER",
)

_PORTABLE_I63_MIN = -(1 << 63)
_PORTABLE_I63_MAX = (1 << 63) - 1
_PORTABLE_U31_MAX = (1 << 31) - 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ATTR_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")

_STRENGTH_RANK = {
    "ADVISORY": 1,
    "PREFERENCE": 2,
    "POLICY": 3,
    "HARD": 4,
    "HARD_FLOOR": 5,
}


def _required_text(name: str, value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"rule {name} is required")
    return text


def _optional_text(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: str) -> str:
    digest = _required_text(name, value).lower()
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(f"rule {name} must be a lowercase 64-hex SHA-256 digest")
    return digest


def _portable_scalar(name: str, value: Any) -> str | int | bool | None:
    if isinstance(value, float):
        raise TypeError(f"binary floating-point is forbidden in rule {name}")
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        if value < _PORTABLE_I63_MIN or value > _PORTABLE_I63_MAX:
            raise ValueError(f"rule {name} integer exceeds portable signed 63-bit bounds")
        return value
    raise TypeError(f"rule {name} must be a portable scalar string/int/bool/null value")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return _jsonable(value.identity_payload())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point is forbidden in rule semantic identity")
    if isinstance(value, int):
        if value < _PORTABLE_I63_MIN or value > _PORTABLE_I63_MAX:
            raise ValueError("rule integer exceeds portable signed 63-bit bounds")
        return value
    if isinstance(value, (str, bool)) or value is None:
        return value
    raise TypeError(f"rule value is not JSON serializable: {type(value)!r}")


def _uniq_text(values: Sequence[str], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not allow_empty and not normalized:
        raise ValueError(f"rule {name} requires at least one value")
    return normalized


def _external_refs(
    values: Sequence[ExternalReference | Mapping[str, Any]],
) -> tuple[ExternalReference, ...]:
    refs = tuple(
        row if isinstance(row, ExternalReference) else ExternalReference.from_dict(dict(row))
        for row in values
    )
    by_fingerprint = {row.fingerprint: row for row in refs}
    if len(by_fingerprint) != len(refs):
        raise ValueError("duplicate external reference in rule contract")
    for row in refs:
        _jsonable(row.identity_payload())
    return tuple(
        sorted(
            refs,
            key=lambda row: (
                row.namespace,
                row.external_id,
                row.role,
                row.revision,
                row.fingerprint,
            ),
        )
    )


def _attribute_map(name: str, value: Mapping[str, Any]) -> dict[str, str | int | bool | None]:
    out: dict[str, str | int | bool | None] = {}
    for raw_key, raw_value in sorted(value.items(), key=lambda pair: str(pair[0])):
        key = _required_text(f"{name} attribute name", str(raw_key))
        if not _ATTR_NAME_RE.fullmatch(key):
            raise ValueError(f"invalid rule attribute identifier: {key}")
        out[key] = _portable_scalar(f"{name}.{key}", raw_value)
    return out


@dataclass(frozen=True)
class RuleClauseRef:
    """Exact semantic object governed by a rule.

    The Rule foundation deliberately does not invent another constraint DSL.
    It binds an exact already-defined semantic clause/predicate/requirement by
    contract ID, stable ID and fingerprint. A later lowering contract may map
    a Rule to solver/calculus objects only if it can preserve this identity.
    """

    clause_contract_id: str
    clause_id: str
    clause_fingerprint: str
    clause_kind: str = "OTHER"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "clause_contract_id", _required_text("clause_contract_id", self.clause_contract_id))
        object.__setattr__(self, "clause_id", _required_text("clause_id", self.clause_id))
        object.__setattr__(self, "clause_fingerprint", _sha256("clause_fingerprint", self.clause_fingerprint))
        kind = _required_text("clause_kind", self.clause_kind).upper()
        if kind not in RULE_CLAUSE_KINDS:
            raise ValueError(f"unsupported rule clause kind: {kind}")
        object.__setattr__(self, "clause_kind", kind)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "clause_contract_id": self.clause_contract_id,
            "clause_id": self.clause_id,
            "clause_fingerprint": self.clause_fingerprint,
            "clause_kind": self.clause_kind,
            "metadata": _jsonable(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleClauseRef":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule clause fingerprint does not match canonical content")
        return item


@dataclass(frozen=True)
class RuleSourceAuthorityRef:
    """Exact reference to the existing scoped-authority plane.

    This object never decides authority. It only binds the principal, existing
    grant identity/fingerprint and required capability that a later admission
    runtime must revalidate through AASM's existing scoped authority system.
    """

    principal_id: str
    authority_grant_id: str
    authority_grant_fingerprint: str
    capability: str = "rule.issue"

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_id", _required_text("source authority principal_id", self.principal_id))
        object.__setattr__(self, "authority_grant_id", _required_text("source authority grant_id", self.authority_grant_id))
        object.__setattr__(
            self,
            "authority_grant_fingerprint",
            _sha256("source authority grant_fingerprint", self.authority_grant_fingerprint),
        )
        object.__setattr__(self, "capability", _required_text("source authority capability", self.capability))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, str]:
        return {
            "principal_id": self.principal_id,
            "authority_grant_id": self.authority_grant_id,
            "authority_grant_fingerprint": self.authority_grant_fingerprint,
            "capability": self.capability,
        }

    def to_dict(self) -> dict[str, str]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleSourceAuthorityRef":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule source authority reference fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RuleScopeSelector:
    workspace_id: str
    scope_id: str = ""
    match_policy: str = "ANY_IN_WORKSPACE"
    subject_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_id", _required_text("scope selector workspace_id", self.workspace_id))
        policy = _required_text("scope selector match_policy", self.match_policy).upper()
        if policy not in RULE_SCOPE_MATCH_POLICIES:
            raise ValueError(f"unsupported rule scope match policy: {policy}")
        scope_id = _optional_text(self.scope_id)
        if policy == "ANY_IN_WORKSPACE" and scope_id:
            raise ValueError("ANY_IN_WORKSPACE rule scope selector must not carry scope_id")
        if policy != "ANY_IN_WORKSPACE" and not scope_id:
            raise ValueError(f"{policy} rule scope selector requires scope_id")
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(self, "match_policy", policy)
        object.__setattr__(self, "subject_ids", _uniq_text(self.subject_ids, name="scope selector subject_ids"))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "match_policy": self.match_policy,
            "subject_ids": list(self.subject_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleScopeSelector":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["subject_ids"] = tuple(payload.get("subject_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule scope selector fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RuleApplicabilityPredicate:
    """Portable, non-executable applicability predicate.

    v0.1 intentionally supports exact context matching only. Unsupported richer
    predicates fail closed rather than embedding Python callbacks, expressions,
    or hidden provider-specific code in durable rule identity.
    """

    kind: str = "ALWAYS"
    required_attributes: Mapping[str, Any] = field(default_factory=dict)
    forbidden_attribute_values: Mapping[str, Any] = field(default_factory=dict)
    required_tags: tuple[str, ...] = ()
    forbidden_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        kind = _required_text("applicability predicate kind", self.kind).upper()
        if kind not in RULE_PREDICATE_KINDS:
            raise ValueError(f"unsupported rule applicability predicate kind: {kind}")
        required = _attribute_map("required", self.required_attributes)
        forbidden = _attribute_map("forbidden", self.forbidden_attribute_values)
        required_tags = _uniq_text(self.required_tags, name="required_tags")
        forbidden_tags = _uniq_text(self.forbidden_tags, name="forbidden_tags")
        if set(required_tags) & set(forbidden_tags):
            raise ValueError("rule applicability predicate cannot require and forbid the same tag")
        if kind == "ALWAYS" and (required or forbidden or required_tags or forbidden_tags):
            raise ValueError("ALWAYS applicability predicate cannot carry context match conditions")
        if kind == "CONTEXT_MATCH" and not (required or forbidden or required_tags or forbidden_tags):
            raise ValueError("CONTEXT_MATCH applicability predicate requires at least one condition")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "required_attributes", required)
        object.__setattr__(self, "forbidden_attribute_values", forbidden)
        object.__setattr__(self, "required_tags", required_tags)
        object.__setattr__(self, "forbidden_tags", forbidden_tags)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "required_attributes": _jsonable(self.required_attributes),
            "forbidden_attribute_values": _jsonable(self.forbidden_attribute_values),
            "required_tags": list(self.required_tags),
            "forbidden_tags": list(self.forbidden_tags),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleApplicabilityPredicate":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["required_attributes"] = dict(payload.get("required_attributes") or {})
        payload["forbidden_attribute_values"] = dict(payload.get("forbidden_attribute_values") or {})
        payload["required_tags"] = tuple(payload.get("required_tags") or ())
        payload["forbidden_tags"] = tuple(payload.get("forbidden_tags") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule applicability predicate fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RuleControlPolicy:
    waiver_mode: str = "FORBIDDEN"
    override_mode: str = "FORBIDDEN"
    required_capability: str = ""

    def __post_init__(self) -> None:
        waiver = _required_text("waiver_mode", self.waiver_mode).upper()
        override = _required_text("override_mode", self.override_mode).upper()
        if waiver not in RULE_WAIVER_MODES:
            raise ValueError(f"unsupported rule waiver mode: {waiver}")
        if override not in RULE_OVERRIDE_MODES:
            raise ValueError(f"unsupported rule override mode: {override}")
        capability = _optional_text(self.required_capability)
        requires_explicit = waiver == "EXPLICIT_AUTHORIZED" or override != "FORBIDDEN"
        if requires_explicit and not capability:
            raise ValueError("explicit rule waiver/override policy requires required_capability")
        if not requires_explicit and capability:
            raise ValueError("forbidden rule waiver/override policy must not carry required_capability")
        object.__setattr__(self, "waiver_mode", waiver)
        object.__setattr__(self, "override_mode", override)
        object.__setattr__(self, "required_capability", capability)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, str]:
        return {
            "waiver_mode": self.waiver_mode,
            "override_mode": self.override_mode,
            "required_capability": self.required_capability,
        }

    def to_dict(self) -> dict[str, str]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleControlPolicy":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule control policy fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RuleApplicabilityContext:
    """Explicit caller-supplied context used to evaluate applicability.

    This context is not authoritative merely because it exists. A future
    runtime admission layer must bind/validate it against existing AASM scope,
    ProblemRevision, external-reference and authority projections.
    """

    workspace_id: str
    scope_id: str
    subject_id: str
    scope_ancestor_ids: tuple[str, ...] = ()
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    attributes: Mapping[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_id", _required_text("applicability context workspace_id", self.workspace_id))
        object.__setattr__(self, "scope_id", _required_text("applicability context scope_id", self.scope_id))
        object.__setattr__(self, "subject_id", _required_text("applicability context subject_id", self.subject_id))
        ancestors = _uniq_text(self.scope_ancestor_ids, name="scope_ancestor_ids")
        if self.scope_id in ancestors:
            raise ValueError("rule applicability context scope_ancestor_ids must not repeat scope_id")
        problem_id = _optional_text(self.problem_revision_id)
        problem_fp = _optional_text(self.problem_revision_fingerprint)
        if bool(problem_id) != bool(problem_fp):
            raise ValueError("rule applicability context problem revision ID and fingerprint must be supplied together")
        if problem_fp:
            problem_fp = _sha256("applicability context problem_revision_fingerprint", problem_fp)
        object.__setattr__(self, "scope_ancestor_ids", ancestors)
        object.__setattr__(self, "problem_revision_id", problem_id)
        object.__setattr__(self, "problem_revision_fingerprint", problem_fp)
        object.__setattr__(self, "external_references", _external_refs(self.external_references))
        object.__setattr__(self, "attributes", _attribute_map("context", self.attributes))
        object.__setattr__(self, "tags", _uniq_text(self.tags, name="context tags"))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "scope_ancestor_ids": list(self.scope_ancestor_ids),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "external_references": [row.identity_payload() for row in self.external_references],
            "attributes": _jsonable(self.attributes),
            "tags": list(self.tags),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RuleApplicabilityContext":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["scope_ancestor_ids"] = tuple(payload.get("scope_ancestor_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        payload["attributes"] = dict(payload.get("attributes") or {})
        payload["tags"] = tuple(payload.get("tags") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("rule applicability context fingerprint mismatch")
        return item


@dataclass(frozen=True)
class EngineeringRule:
    """Immutable source engineering/policy rule semantic envelope.

    This is deliberately distinct from AASM's learned HARD/SOFT conflict
    constraints and from objective vectors. The foundation records identity,
    applicability and precedence metadata only; it does not lower or execute
    the semantic clause and cannot mint truth/effect authority.
    """

    rule_id: str
    clause: RuleClauseRef | Mapping[str, Any]
    strength: str
    scope_selector: RuleScopeSelector | Mapping[str, Any]
    applicability: RuleApplicabilityPredicate | Mapping[str, Any]
    precedence_group: str
    priority: int = 0
    specificity: int = 0
    control_policy: RuleControlPolicy | Mapping[str, Any] = field(default_factory=RuleControlPolicy)
    severity: str = "MEDIUM"
    source_authority: RuleSourceAuthorityRef | Mapping[str, Any] | None = None
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    applicable_external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    rule_revision_id: str = ""
    contract_id: str = RULE_CONTRACT_ID
    contract_version: str = RULE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != RULE_CONTRACT_ID or self.contract_version != RULE_CONTRACT_VERSION:
            raise ValueError("unsupported engineering rule contract")
        object.__setattr__(self, "rule_id", _required_text("rule_id", self.rule_id))
        clause = self.clause if isinstance(self.clause, RuleClauseRef) else RuleClauseRef.from_dict(self.clause)
        selector = (
            self.scope_selector
            if isinstance(self.scope_selector, RuleScopeSelector)
            else RuleScopeSelector.from_dict(self.scope_selector)
        )
        predicate = (
            self.applicability
            if isinstance(self.applicability, RuleApplicabilityPredicate)
            else RuleApplicabilityPredicate.from_dict(self.applicability)
        )
        strength = _required_text("strength", self.strength).upper()
        if strength not in RULE_STRENGTHS:
            raise ValueError(f"unsupported engineering rule strength: {strength}")
        precedence_group = _required_text("precedence_group", self.precedence_group)
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("rule priority must be an exact integer")
        if self.priority < _PORTABLE_I63_MIN or self.priority > _PORTABLE_I63_MAX:
            raise ValueError("rule priority exceeds portable signed 63-bit bounds")
        if isinstance(self.specificity, bool) or not isinstance(self.specificity, int):
            raise TypeError("rule specificity must be an exact non-negative integer")
        if self.specificity < 0 or self.specificity > _PORTABLE_U31_MAX:
            raise ValueError("rule specificity exceeds portable non-negative 31-bit bounds")
        control = (
            self.control_policy
            if isinstance(self.control_policy, RuleControlPolicy)
            else RuleControlPolicy.from_dict(self.control_policy)
        )
        severity = _required_text("severity", self.severity).upper()
        if severity not in RULE_SEVERITIES:
            raise ValueError(f"unsupported engineering rule severity: {severity}")
        authority = self.source_authority
        if authority is not None and not isinstance(authority, RuleSourceAuthorityRef):
            authority = RuleSourceAuthorityRef.from_dict(authority)
        problem_id = _optional_text(self.problem_revision_id)
        problem_fp = _optional_text(self.problem_revision_fingerprint)
        if bool(problem_id) != bool(problem_fp):
            raise ValueError("rule problem revision ID and fingerprint must be supplied together")
        if problem_fp:
            problem_fp = _sha256("problem_revision_fingerprint", problem_fp)
        external_refs = _external_refs(self.applicable_external_references)
        evidence_ids = _uniq_text(self.evidence_ids, name="evidence_ids")
        metadata = _jsonable(dict(self.metadata))
        if strength == "HARD_FLOOR" and (
            control.waiver_mode != "FORBIDDEN" or control.override_mode != "FORBIDDEN"
        ):
            raise ValueError("HARD_FLOOR rules cannot be waived or overridden")

        object.__setattr__(self, "clause", clause)
        object.__setattr__(self, "scope_selector", selector)
        object.__setattr__(self, "applicability", predicate)
        object.__setattr__(self, "strength", strength)
        object.__setattr__(self, "precedence_group", precedence_group)
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "specificity", int(self.specificity))
        object.__setattr__(self, "control_policy", control)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "source_authority", authority)
        object.__setattr__(self, "problem_revision_id", problem_id)
        object.__setattr__(self, "problem_revision_fingerprint", problem_fp)
        object.__setattr__(self, "applicable_external_references", external_refs)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "metadata", metadata)

        derived = f"rule-revision-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional_text(self.rule_revision_id)
        if supplied and supplied != derived:
            raise ValueError("rule_revision_id does not match canonical rule identity")
        object.__setattr__(self, "rule_revision_id", derived)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"rule_revision_id": self.rule_revision_id, **self.identity_payload()})

    @property
    def precedence_key(self) -> tuple[int, int, int]:
        return (_STRENGTH_RANK[self.strength], self.specificity, self.priority)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "rule_id": self.rule_id,
            "clause": self.clause.identity_payload(),
            "strength": self.strength,
            "scope_selector": self.scope_selector.identity_payload(),
            "applicability": self.applicability.identity_payload(),
            "precedence_group": self.precedence_group,
            "priority": self.priority,
            "specificity": self.specificity,
            "control_policy": self.control_policy.identity_payload(),
            "severity": self.severity,
            "source_authority": None if self.source_authority is None else self.source_authority.identity_payload(),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "applicable_external_references": [
                row.identity_payload() for row in self.applicable_external_references
            ],
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_revision_id": self.rule_revision_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EngineeringRule":
        payload = deepcopy(dict(value))
        supplied_fingerprint = str(payload.pop("fingerprint", "")).strip()
        payload["clause"] = RuleClauseRef.from_dict(payload["clause"])
        payload["scope_selector"] = RuleScopeSelector.from_dict(payload["scope_selector"])
        payload["applicability"] = RuleApplicabilityPredicate.from_dict(payload["applicability"])
        payload["control_policy"] = RuleControlPolicy.from_dict(payload["control_policy"])
        if payload.get("source_authority") is not None:
            payload["source_authority"] = RuleSourceAuthorityRef.from_dict(payload["source_authority"])
        payload["applicable_external_references"] = tuple(payload.get("applicable_external_references") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["metadata"] = dict(payload.get("metadata") or {})
        item = cls(**payload)
        if supplied_fingerprint and supplied_fingerprint != item.fingerprint:
            raise ValueError("engineering rule fingerprint does not match canonical content")
        return item


@dataclass(frozen=True)
class RuleApplicabilityAssessment:
    rule_revision_id: str
    rule_fingerprint: str
    context_fingerprint: str
    result: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "rule_revision_id", _required_text("assessment rule_revision_id", self.rule_revision_id))
        object.__setattr__(self, "rule_fingerprint", _sha256("assessment rule_fingerprint", self.rule_fingerprint))
        object.__setattr__(self, "context_fingerprint", _sha256("assessment context_fingerprint", self.context_fingerprint))
        result = _required_text("assessment result", self.result).upper()
        if result not in RULE_APPLICABILITY_RESULTS:
            raise ValueError(f"unsupported rule applicability result: {result}")
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "reasons", _uniq_text(self.reasons, name="assessment reasons"))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "context_fingerprint": self.context_fingerprint,
            "result": self.result,
            "reasons": list(self.reasons),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}


def _scope_applicability(rule: EngineeringRule, context: RuleApplicabilityContext) -> tuple[str, list[str]]:
    selector = rule.scope_selector
    reasons: list[str] = []
    if selector.workspace_id != context.workspace_id:
        return "NOT_APPLICABLE", ["WORKSPACE_MISMATCH"]
    if selector.subject_ids and context.subject_id not in selector.subject_ids:
        return "NOT_APPLICABLE", ["SUBJECT_NOT_SELECTED"]
    if selector.match_policy == "EXACT" and selector.scope_id != context.scope_id:
        return "NOT_APPLICABLE", ["SCOPE_MISMATCH"]
    if selector.match_policy == "DESCENDANT_OR_SELF":
        if selector.scope_id != context.scope_id and selector.scope_id not in context.scope_ancestor_ids:
            return "NOT_APPLICABLE", ["SCOPE_NOT_DESCENDANT"]
    return "APPLICABLE", reasons


def _revision_applicability(rule: EngineeringRule, context: RuleApplicabilityContext) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if rule.problem_revision_id:
        if not context.problem_revision_id:
            return "INDETERMINATE", ["PROBLEM_REVISION_CONTEXT_MISSING"]
        if (
            rule.problem_revision_id != context.problem_revision_id
            or rule.problem_revision_fingerprint != context.problem_revision_fingerprint
        ):
            return "NOT_APPLICABLE", ["PROBLEM_REVISION_MISMATCH"]

    context_by_identity = {
        (ref.namespace, ref.external_id, ref.role): ref
        for ref in context.external_references
    }
    for required in rule.applicable_external_references:
        key = (required.namespace, required.external_id, required.role)
        observed = context_by_identity.get(key)
        if observed is None:
            reasons.append(f"EXTERNAL_REFERENCE_CONTEXT_MISSING:{required.namespace}:{required.external_id}:{required.role}")
            continue
        if observed.fingerprint != required.fingerprint:
            return "NOT_APPLICABLE", [f"EXTERNAL_REFERENCE_MISMATCH:{required.namespace}:{required.external_id}:{required.role}"]
    if reasons:
        return "INDETERMINATE", reasons
    return "APPLICABLE", []


def _predicate_applicability(
    predicate: RuleApplicabilityPredicate,
    context: RuleApplicabilityContext,
) -> tuple[str, list[str]]:
    if predicate.kind == "ALWAYS":
        return "APPLICABLE", []
    reasons: list[str] = []
    for key, required in predicate.required_attributes.items():
        if key not in context.attributes:
            reasons.append(f"REQUIRED_ATTRIBUTE_MISSING:{key}")
        elif context.attributes[key] != required:
            return "NOT_APPLICABLE", [f"REQUIRED_ATTRIBUTE_MISMATCH:{key}"]
    if reasons:
        return "INDETERMINATE", reasons
    for key, forbidden in predicate.forbidden_attribute_values.items():
        if key in context.attributes and context.attributes[key] == forbidden:
            return "NOT_APPLICABLE", [f"FORBIDDEN_ATTRIBUTE_VALUE:{key}"]
    context_tags = set(context.tags)
    missing_tags = sorted(set(predicate.required_tags) - context_tags)
    if missing_tags:
        return "NOT_APPLICABLE", [f"REQUIRED_TAG_MISSING:{tag}" for tag in missing_tags]
    forbidden_tags = sorted(set(predicate.forbidden_tags) & context_tags)
    if forbidden_tags:
        return "NOT_APPLICABLE", [f"FORBIDDEN_TAG_PRESENT:{tag}" for tag in forbidden_tags]
    return "APPLICABLE", []


def evaluate_rule_applicability(
    rule: EngineeringRule,
    context: RuleApplicabilityContext,
) -> RuleApplicabilityAssessment:
    stages = (
        _scope_applicability(rule, context),
        _revision_applicability(rule, context),
        _predicate_applicability(rule.applicability, context),
    )
    indeterminate: list[str] = []
    for result, reasons in stages:
        if result == "NOT_APPLICABLE":
            return RuleApplicabilityAssessment(
                rule.rule_revision_id,
                rule.fingerprint,
                context.fingerprint,
                result,
                tuple(reasons),
            )
        if result == "INDETERMINATE":
            indeterminate.extend(reasons)
    result = "INDETERMINATE" if indeterminate else "APPLICABLE"
    return RuleApplicabilityAssessment(
        rule.rule_revision_id,
        rule.fingerprint,
        context.fingerprint,
        result,
        tuple(indeterminate),
    )


def compare_rule_precedence(left: EngineeringRule, right: EngineeringRule) -> str:
    """Compare structural precedence without authorizing override or waiver."""

    if left.precedence_group != right.precedence_group:
        return "INCOMPARABLE"
    if left.precedence_key > right.precedence_key:
        return "LEFT_PRECEDES"
    if right.precedence_key > left.precedence_key:
        return "RIGHT_PRECEDES"
    return "EQUIVALENT_PRECEDENCE"


def rule_waiver_structurally_eligible(rule: EngineeringRule, presented_capability: str) -> bool:
    """Return structural eligibility only; this never verifies authority."""

    if rule.strength == "HARD_FLOOR" or rule.control_policy.waiver_mode == "FORBIDDEN":
        return False
    return _optional_text(presented_capability) == rule.control_policy.required_capability


def rule_override_structurally_eligible(
    base_rule: EngineeringRule,
    challenger: EngineeringRule,
    presented_capability: str,
) -> bool:
    """Return structural eligibility only; this never verifies authority."""

    if base_rule.precedence_group != challenger.precedence_group:
        return False
    if base_rule.strength == "HARD_FLOOR":
        return False
    policy = base_rule.control_policy
    if policy.override_mode == "FORBIDDEN":
        return False
    if _optional_text(presented_capability) != policy.required_capability:
        return False
    base_rank = _STRENGTH_RANK[base_rule.strength]
    challenger_rank = _STRENGTH_RANK[challenger.strength]
    if policy.override_mode == "STRICTLY_STRONGER_EXPLICIT":
        return challenger_rank > base_rank
    return challenger_rank >= base_rank


def rule_contract() -> dict[str, Any]:
    return {
        "contract_id": RULE_CONTRACT_ID,
        "contract_version": RULE_CONTRACT_VERSION,
        "stability": RULE_STABILITY,
        "strengths": list(RULE_STRENGTHS),
        "applicability": "EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED",
        "predicate_scope": "ALWAYS_OR_EXACT_CONTEXT_MATCH_ONLY_NO_EXECUTABLE_CALLBACKS",
        "scope_selector": "EXPLICIT_WORKSPACE_SCOPE_SUBJECT_WITH_CALLER_SUPPLIED_ANCESTRY",
        "scope_context_authority": "NONE_CALLER_CONTEXT_MUST_BE_VALIDATED_AT_RUNTIME_ADMISSION",
        "revision_applicability": "EXACT_PROBLEM_AND_EXTERNAL_REFERENCE_IDENTITY",
        "precedence": "STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP",
        "precedence_is_objective_priority": False,
        "precedence_authorizes_override": False,
        "hard_floor_waiver": "FORBIDDEN",
        "hard_floor_override": "FORBIDDEN",
        "waiver_override_authority": "STRUCTURAL_ELIGIBILITY_ONLY_EXISTING_SCOPED_AUTHORITY_MUST_AUTHORIZE_LATER_RUNTIME_ACTION",
        "source_authority": "EXACT_EXISTING_SCOPED_AUTHORITY_GRANT_REFERENCE_ONLY_NOT_VERIFIED_BY_FOUNDATION",
        "rule_clause": "EXACT_EXTERNAL_OR_EXISTING_SEMANTIC_CLAUSE_ID_AND_FINGERPRINT_NO_NEW_CONSTRAINT_DSL",
        "learned_constraint_relation": "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT",
        "rule_to_constraint_lowering": "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED",
        "rule_existence_grants_fact_authority": False,
        "rule_existence_grants_effect_authority": False,
        "rule_existence_grants_source_authority": False,
        "parallel_rule_registry": "NONE",
        "current_rule_pointer": "NONE",
        "parallel_constraint_engine": "NONE",
        "parallel_authority_evaluator": "NONE",
        "hidden_wall_clock": "NONE",
        "portable_integer_bounds": "SIGNED_63_PRIORITY_UNSIGNED_31_SPECIFICITY",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "RULE_CONTRACT_ID",
    "RULE_CONTRACT_VERSION",
    "RULE_STABILITY",
    "RULE_STRENGTHS",
    "RULE_SEVERITIES",
    "RULE_SCOPE_MATCH_POLICIES",
    "RULE_PREDICATE_KINDS",
    "RULE_WAIVER_MODES",
    "RULE_OVERRIDE_MODES",
    "RULE_APPLICABILITY_RESULTS",
    "RULE_PRECEDENCE_RELATIONS",
    "RULE_CLAUSE_KINDS",
    "RuleClauseRef",
    "RuleSourceAuthorityRef",
    "RuleScopeSelector",
    "RuleApplicabilityPredicate",
    "RuleControlPolicy",
    "RuleApplicabilityContext",
    "EngineeringRule",
    "RuleApplicabilityAssessment",
    "evaluate_rule_applicability",
    "compare_rule_precedence",
    "rule_waiver_structurally_eligible",
    "rule_override_structurally_eligible",
    "rule_contract",
]
