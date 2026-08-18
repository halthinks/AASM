from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .calculus import (
    OBLIGATION_STATUSES,
    OBLIGATION_TRANSITIONS,
    ObligationRecord,
    content_hash,
    normalize_calculus_state,
)
from .scopes import ROOT_SCOPE_ID, scope_id_from, with_scope
from .semantic_result import semantic_fingerprint


OBLIGATION_PHASE_CONTRACT_ID = "aasm.obligation.phase.v1"
OBLIGATION_PHASE_CONTRACT_VERSION = "0.1.0"
OBLIGATION_PHASE_BINDING_CONTRACT_ID = "aasm.obligation.phase-binding.v1"
OBLIGATION_PHASE_BINDING_CONTRACT_VERSION = "0.1.0"
OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID = "aasm.obligation.phase-assessment.v1"
OBLIGATION_PHASE_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
OBLIGATION_PHASE_STABILITY = "FOUNDATION_EXPERIMENTAL"
CALCULUS_SUBSTRATE_ID = "aasm.calculus.v1"
CALCULUS_STATE_SCHEMA_VERSION = 1
OBLIGATION_BINDING_PROJECTION_ID = "aasm.obligation.phase.binding-projection.v1"

OBLIGATION_PHASES = (
    "PRE_AUTHORIZE",
    "PRE_DISPATCH",
    "POST_DISPATCH",
    "POST_OBSERVE",
    "POST_VERIFY",
    "RECOVERY",
)
NORMAL_OBLIGATION_PHASES = OBLIGATION_PHASES[:-1]
OBLIGATION_PHASE_READINESS = ("READY", "NOT_READY", "TERMINAL_UNSATISFIED")
SATISFIED_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
TERMINAL_UNSATISFIED_OBLIGATION_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NORMAL_PHASE_RANK = {phase: index for index, phase in enumerate(NORMAL_OBLIGATION_PHASES)}


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"obligation-phase {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"obligation-phase {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _jsonable(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return _jsonable(value.identity_payload())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in obligation-phase portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"obligation-phase value is not JSON serializable: {type(value)!r}")


def _phase(value: Any) -> str:
    phase = _required("phase", value).upper()
    if phase not in OBLIGATION_PHASES:
        raise ValueError(f"unsupported obligation phase: {phase}")
    return phase


def _canonical_obligation(value: ObligationRecord | Mapping[str, Any]) -> dict[str, Any]:
    row = value.to_dict() if isinstance(value, ObligationRecord) else deepcopy(dict(value))
    obligation_id = _required("obligation_id", row.get("obligation_id"))
    statement = _required("obligation statement", row.get("statement"))
    status = _required("obligation status", row.get("status", "AVAILABLE")).upper()
    if status not in OBLIGATION_STATUSES:
        raise ValueError(f"unsupported existing obligation status: {status}")
    row["obligation_id"] = obligation_id
    row["statement"] = statement
    row["status"] = status
    scope_id = scope_id_from(row)
    row["scope"] = with_scope(row.get("scope") if isinstance(row.get("scope"), Mapping) else {}, scope_id)
    return row


def obligation_binding_projection(value: ObligationRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Project stable obligation requirements for phase-binding staleness checks.

    This is deliberately not an ObligationRecord identity or replacement.  The
    live calculus has no native obligation fingerprint contract.  S4.7 binds
    only to a versioned semantic projection and leaves the canonical
    obligation_id, store, status machine, evidence attachment, locks, attempts,
    fairness, and mutation ownership unchanged.
    """
    row = _canonical_obligation(value)
    projection = {
        "projection_id": OBLIGATION_BINDING_PROJECTION_ID,
        "obligation_id": row["obligation_id"],
        "statement": row["statement"],
        "activation_condition": deepcopy(row.get("activation_condition") or {"const": True}),
        "dependencies": sorted({str(v) for v in row.get("dependencies", [])}),
        "decision_dependencies": sorted({str(v) for v in row.get("decision_dependencies", [])}),
        "plan_node_ids": sorted({str(v) for v in row.get("plan_node_ids", [])}),
        "required_evidence_types": sorted({str(v) for v in row.get("required_evidence_types", [])}),
        "persistent": bool(row.get("persistent", True)),
        "mandatory": bool(row.get("mandatory", True)),
        "scope": with_scope(row.get("scope") if isinstance(row.get("scope"), Mapping) else {}, scope_id_from(row)),
    }
    return _jsonable(projection)


def obligation_semantic_fingerprint(value: ObligationRecord | Mapping[str, Any]) -> str:
    """Hash the S4.7 binding projection with the existing calculus content hash."""
    return content_hash(obligation_binding_projection(value))


def phase_relation(left: str, right: str) -> str:
    """Compare applicability phases without inventing an order for RECOVERY."""
    left_phase = _phase(left)
    right_phase = _phase(right)
    if left_phase == right_phase:
        return "SAME_PHASE"
    if left_phase == "RECOVERY" or right_phase == "RECOVERY":
        return "INCOMPARABLE"
    if _NORMAL_PHASE_RANK[left_phase] < _NORMAL_PHASE_RANK[right_phase]:
        return "PRECEDES"
    return "FOLLOWS"


@dataclass(frozen=True)
class ObligationPhaseBinding:
    obligation_id: str
    obligation_semantic_fingerprint: str
    phase: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    scope_id: str = ROOT_SCOPE_ID
    metadata: Mapping[str, Any] = field(default_factory=dict)
    binding_id: str = ""
    contract_id: str = OBLIGATION_PHASE_BINDING_CONTRACT_ID
    contract_version: str = OBLIGATION_PHASE_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != OBLIGATION_PHASE_BINDING_CONTRACT_ID or self.contract_version != OBLIGATION_PHASE_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported obligation phase-binding contract")
        obligation_id = _required("obligation_id", self.obligation_id)
        fingerprint = _sha256("obligation_semantic_fingerprint", self.obligation_semantic_fingerprint)
        phase = _phase(self.phase)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint)
        scope_id = _required("scope_id", self.scope_id)
        metadata = _jsonable(dict(self.metadata))
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "obligation_semantic_fingerprint", fingerprint)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(self, "metadata", metadata)
        derived = f"obligation-phase-binding-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.binding_id)
        if supplied and supplied != derived:
            raise ValueError("obligation phase binding_id does not match canonical identity")
        object.__setattr__(self, "binding_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "phase": self.phase,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "scope_id": self.scope_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObligationPhaseBinding":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("obligation phase binding fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ObligationPhasePlan:
    problem_revision_id: str
    problem_revision_fingerprint: str
    bindings: tuple[ObligationPhaseBinding | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    plan_id: str = ""
    contract_id: str = OBLIGATION_PHASE_CONTRACT_ID
    contract_version: str = OBLIGATION_PHASE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != OBLIGATION_PHASE_CONTRACT_ID or self.contract_version != OBLIGATION_PHASE_CONTRACT_VERSION:
            raise ValueError("unsupported obligation-phase contract")
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint)
        bindings = tuple(
            value if isinstance(value, ObligationPhaseBinding) else ObligationPhaseBinding.from_dict(value)
            for value in self.bindings
        )
        ids = [value.obligation_id for value in bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("obligation phase plan requires exactly one binding per obligation_id")
        for binding in bindings:
            if binding.problem_revision_id != revision_id or binding.problem_revision_fingerprint != revision_fingerprint:
                raise ValueError("all obligation phase bindings must use the exact plan ProblemRevision")
        bindings = tuple(sorted(bindings, key=lambda value: value.obligation_id))
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"obligation-phase-plan-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.plan_id)
        if supplied and supplied != derived:
            raise ValueError("obligation phase plan_id does not match canonical identity")
        object.__setattr__(self, "plan_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "bindings": [value.identity_payload() for value in self.bindings],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"plan_id": self.plan_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObligationPhasePlan":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["bindings"] = tuple(payload.get("bindings") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("obligation phase plan fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ObligationPhaseAssessment:
    plan_id: str
    plan_fingerprint: str
    phase: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    readiness: str
    required_obligation_ids: tuple[str, ...]
    satisfied_obligation_ids: tuple[str, ...]
    blocking_obligation_ids: tuple[str, ...]
    terminal_unsatisfied_obligation_ids: tuple[str, ...]
    observed_statuses: Mapping[str, str]
    reasons: tuple[str, ...] = ()
    assessment_id: str = ""
    contract_id: str = OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID
    contract_version: str = OBLIGATION_PHASE_ASSESSMENT_CONTRACT_VERSION
    effect_authority_granted: bool = False
    authorization_performed: bool = False
    dispatch_performed: bool = False
    recovery_execution_performed: bool = False
    obligation_status_mutated: bool = False
    phase_activated: bool = False

    def __post_init__(self) -> None:
        if self.contract_id != OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID or self.contract_version != OBLIGATION_PHASE_ASSESSMENT_CONTRACT_VERSION:
            raise ValueError("unsupported obligation phase-assessment contract")
        plan_id = _required("plan_id", self.plan_id)
        plan_fingerprint = _sha256("plan_fingerprint", self.plan_fingerprint)
        phase = _phase(self.phase)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint)
        readiness = _required("readiness", self.readiness).upper()
        if readiness not in OBLIGATION_PHASE_READINESS:
            raise ValueError(f"unsupported obligation phase readiness: {readiness}")

        def ids(values: Sequence[Any], name: str) -> tuple[str, ...]:
            return tuple(sorted({_required(name, value) for value in values}))

        required = ids(self.required_obligation_ids, "required obligation_id")
        satisfied = ids(self.satisfied_obligation_ids, "satisfied obligation_id")
        blocking = ids(self.blocking_obligation_ids, "blocking obligation_id")
        terminal = ids(self.terminal_unsatisfied_obligation_ids, "terminal obligation_id")
        if not set(satisfied).issubset(required) or not set(blocking).issubset(required) or not set(terminal).issubset(required):
            raise ValueError("obligation phase assessment result sets must be subsets of required obligations")
        if set(satisfied) & (set(blocking) | set(terminal)) or set(blocking) & set(terminal):
            raise ValueError("obligation phase assessment result sets must be disjoint")
        statuses = {
            str(key): _required("observed obligation status", value).upper()
            for key, value in sorted(self.observed_statuses.items())
        }
        if set(statuses) != set(required):
            raise ValueError("obligation phase observed statuses must exactly cover required obligations")
        for status in statuses.values():
            if status not in OBLIGATION_STATUSES:
                raise ValueError(f"unsupported observed obligation status: {status}")
        reasons = ids(self.reasons, "assessment reason")
        for name in (
            "effect_authority_granted",
            "authorization_performed",
            "dispatch_performed",
            "recovery_execution_performed",
            "obligation_status_mutated",
            "phase_activated",
        ):
            if bool(getattr(self, name)):
                raise ValueError(f"obligation phase assessment cannot set {name}=True")
        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "plan_fingerprint", plan_fingerprint)
        object.__setattr__(self, "phase", phase)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "readiness", readiness)
        object.__setattr__(self, "required_obligation_ids", required)
        object.__setattr__(self, "satisfied_obligation_ids", satisfied)
        object.__setattr__(self, "blocking_obligation_ids", blocking)
        object.__setattr__(self, "terminal_unsatisfied_obligation_ids", terminal)
        object.__setattr__(self, "observed_statuses", statuses)
        object.__setattr__(self, "reasons", reasons)
        derived = f"obligation-phase-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError("obligation phase assessment_id does not match canonical identity")
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "plan_id": self.plan_id,
            "plan_fingerprint": self.plan_fingerprint,
            "phase": self.phase,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "readiness": self.readiness,
            "required_obligation_ids": list(self.required_obligation_ids),
            "satisfied_obligation_ids": list(self.satisfied_obligation_ids),
            "blocking_obligation_ids": list(self.blocking_obligation_ids),
            "terminal_unsatisfied_obligation_ids": list(self.terminal_unsatisfied_obligation_ids),
            "observed_statuses": _jsonable(self.observed_statuses),
            "reasons": list(self.reasons),
            "effect_authority_granted": self.effect_authority_granted,
            "authorization_performed": self.authorization_performed,
            "dispatch_performed": self.dispatch_performed,
            "recovery_execution_performed": self.recovery_execution_performed,
            "obligation_status_mutated": self.obligation_status_mutated,
            "phase_activated": self.phase_activated,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assessment_id": self.assessment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObligationPhaseAssessment":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        for name in (
            "required_obligation_ids",
            "satisfied_obligation_ids",
            "blocking_obligation_ids",
            "terminal_unsatisfied_obligation_ids",
            "reasons",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("obligation phase assessment fingerprint mismatch")
        return item


def bind_obligation_phase(
    obligation: ObligationRecord | Mapping[str, Any],
    phase: str,
    *,
    problem_revision_id: str,
    problem_revision_fingerprint: str,
    metadata: Mapping[str, Any] | None = None,
) -> ObligationPhaseBinding:
    row = _canonical_obligation(obligation)
    return ObligationPhaseBinding(
        obligation_id=row["obligation_id"],
        obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
        phase=phase,
        problem_revision_id=problem_revision_id,
        problem_revision_fingerprint=problem_revision_fingerprint,
        scope_id=scope_id_from(row),
        metadata=dict(metadata or {}),
    )


def validate_obligation_phase_binding(
    binding: ObligationPhaseBinding | Mapping[str, Any],
    obligation: ObligationRecord | Mapping[str, Any],
) -> dict[str, Any]:
    item = binding if isinstance(binding, ObligationPhaseBinding) else ObligationPhaseBinding.from_dict(binding)
    row = _canonical_obligation(obligation)
    if item.obligation_id != row["obligation_id"]:
        raise ValueError("obligation phase binding obligation_id mismatch")
    actual_fingerprint = obligation_semantic_fingerprint(row)
    if item.obligation_semantic_fingerprint != actual_fingerprint:
        raise ValueError("obligation phase binding is stale or mismatched for S4.7 obligation semantic projection")
    actual_scope = scope_id_from(row)
    if item.scope_id != actual_scope:
        raise ValueError("obligation phase binding scope_id mismatch")
    return {
        "valid": True,
        "binding_id": item.binding_id,
        "binding_fingerprint": item.fingerprint,
        "binding_projection_id": OBLIGATION_BINDING_PROJECTION_ID,
        "obligation_id": item.obligation_id,
        "obligation_semantic_fingerprint": actual_fingerprint,
        "scope_id": actual_scope,
        "phase": item.phase,
    }


def validate_obligation_phase_plan(
    calculus_state: Mapping[str, Any],
    plan: ObligationPhasePlan | Mapping[str, Any],
) -> dict[str, Any]:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    if int(state.get("schema_version", -1)) != CALCULUS_STATE_SCHEMA_VERSION:
        raise ValueError("obligation phase plan requires the existing calculus state schema_version 1")
    item = plan if isinstance(plan, ObligationPhasePlan) else ObligationPhasePlan.from_dict(plan)
    obligations = dict(state.get("obligations") or {})
    bindings = {binding.obligation_id: binding for binding in item.bindings}
    if set(bindings) != set(obligations):
        missing = sorted(set(obligations) - set(bindings))
        extra = sorted(set(bindings) - set(obligations))
        raise ValueError(f"obligation phase plan must bind every existing obligation exactly once; missing={missing}, extra={extra}")
    for obligation_id, binding in bindings.items():
        validate_obligation_phase_binding(binding, obligations[obligation_id])

    expected_edges = {
        (str(dependency), str(obligation_id), "REQUIRES")
        for obligation_id, obligation in obligations.items()
        for dependency in obligation.get("dependencies", [])
    }
    actual_edges: set[tuple[str, str, str]] = set()
    raw_edges = list(state.get("obligation_edges", []))
    for raw in raw_edges:
        edge = dict(raw)
        relation = _required("obligation edge relation", edge.get("relation"))
        src = _required("obligation edge src", edge.get("src"))
        dst = _required("obligation edge dst", edge.get("dst"))
        if src not in obligations or dst not in obligations:
            raise ValueError("obligation phase plan encountered edge with unknown canonical obligation")
        if src == dst:
            raise ValueError("obligation phase plan encountered self-referential obligation edge")
        key = (src, dst, relation)
        if key in actual_edges:
            raise ValueError("obligation phase plan encountered duplicate canonical obligation edge")
        actual_edges.add(key)
    if actual_edges != expected_edges:
        raise ValueError("canonical obligation_edges must exactly represent ObligationRecord.dependencies before phase validation")

    backward_edges: list[dict[str, str]] = []
    recovery_edges: list[dict[str, str]] = []
    for src, dst, relation in sorted(actual_edges):
        if relation != "REQUIRES":
            raise ValueError(f"unsupported obligation edge relation for phase foundation: {relation}")
        src_phase = bindings[src].phase
        dst_phase = bindings[dst].phase
        relation_name = phase_relation(src_phase, dst_phase)
        if relation_name == "FOLLOWS":
            backward_edges.append({"src": src, "dst": dst, "src_phase": src_phase, "dst_phase": dst_phase})
        if relation_name == "INCOMPARABLE":
            recovery_edges.append({"src": src, "dst": dst, "src_phase": src_phase, "dst_phase": dst_phase})
    if backward_edges:
        raise ValueError(f"normal obligation phase dependency points backward across boundary order: {backward_edges}")

    return {
        "valid": True,
        "plan_id": item.plan_id,
        "plan_fingerprint": item.fingerprint,
        "calculus_state_schema_version": CALCULUS_STATE_SCHEMA_VERSION,
        "binding_projection_id": OBLIGATION_BINDING_PROJECTION_ID,
        "obligation_count": len(obligations),
        "edge_count": len(actual_edges),
        "recovery_edges": recovery_edges,
        "normal_phase_order": list(NORMAL_OBLIGATION_PHASES),
        "recovery_phase_order": "INCOMPARABLE_USE_EXPLICIT_REQUIRES_EDGES_ONLY",
    }


def assess_obligation_phase_readiness(
    calculus_state: Mapping[str, Any],
    plan: ObligationPhasePlan | Mapping[str, Any],
    phase: str,
    *,
    problem_revision_id: str,
    problem_revision_fingerprint: str,
) -> ObligationPhaseAssessment:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    item = plan if isinstance(plan, ObligationPhasePlan) else ObligationPhasePlan.from_dict(plan)
    validate_obligation_phase_plan(state, item)
    requested_phase = _phase(phase)
    revision_id = _required("problem_revision_id", problem_revision_id)
    revision_fingerprint = _sha256("problem_revision_fingerprint", problem_revision_fingerprint)
    if revision_id != item.problem_revision_id or revision_fingerprint != item.problem_revision_fingerprint:
        raise ValueError("obligation phase readiness requires the exact plan ProblemRevision")

    required = tuple(binding.obligation_id for binding in item.bindings if binding.phase == requested_phase)
    observed = {
        obligation_id: str(state["obligations"][obligation_id]["status"])
        for obligation_id in required
    }
    satisfied = tuple(sorted(
        obligation_id for obligation_id, status in observed.items()
        if status in SATISFIED_OBLIGATION_STATUSES
    ))
    terminal = tuple(sorted(
        obligation_id for obligation_id, status in observed.items()
        if status in TERMINAL_UNSATISFIED_OBLIGATION_STATUSES
    ))
    blocking = tuple(sorted(set(required) - set(satisfied) - set(terminal)))
    reasons: list[str] = []
    if terminal:
        readiness = "TERMINAL_UNSATISFIED"
        reasons.extend(f"TERMINAL_UNSATISFIED:{obligation_id}:{observed[obligation_id]}" for obligation_id in terminal)
    elif blocking:
        readiness = "NOT_READY"
        reasons.extend(f"NOT_SATISFIED:{obligation_id}:{observed[obligation_id]}" for obligation_id in blocking)
    else:
        readiness = "READY"
        if not required:
            reasons.append("NO_OBLIGATIONS_FOR_PHASE")

    return ObligationPhaseAssessment(
        plan_id=item.plan_id,
        plan_fingerprint=item.fingerprint,
        phase=requested_phase,
        problem_revision_id=item.problem_revision_id,
        problem_revision_fingerprint=item.problem_revision_fingerprint,
        readiness=readiness,
        required_obligation_ids=required,
        satisfied_obligation_ids=satisfied,
        blocking_obligation_ids=blocking,
        terminal_unsatisfied_obligation_ids=terminal,
        observed_statuses=observed,
        reasons=tuple(reasons),
    )


def obligation_phase_contract() -> dict[str, Any]:
    return {
        "contract_id": OBLIGATION_PHASE_CONTRACT_ID,
        "contract_version": OBLIGATION_PHASE_CONTRACT_VERSION,
        "binding_contract_id": OBLIGATION_PHASE_BINDING_CONTRACT_ID,
        "assessment_contract_id": OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID,
        "stability": OBLIGATION_PHASE_STABILITY,
        "calculus_contract_id": CALCULUS_SUBSTRATE_ID,
        "calculus_state_schema_version": CALCULUS_STATE_SCHEMA_VERSION,
        "obligation_type": "EXISTING_AASM_CALCULUS_V1_OBLIGATION_RECORD_ONLY",
        "obligation_identity": "EXISTING_OBLIGATION_ID_UNCHANGED_NO_NEW_OBLIGATION_IDENTITY",
        "binding_projection_id": OBLIGATION_BINDING_PROJECTION_ID,
        "binding_projection": "VERSIONED_STABLE_REQUIREMENT_PROJECTION_HASHED_WITH_EXISTING_CALCULUS_CONTENT_HASH",
        "binding_projection_includes": [
            "obligation_id", "statement", "activation_condition", "dependencies", "decision_dependencies",
            "plan_node_ids", "required_evidence_types", "persistent", "mandatory", "scope",
        ],
        "binding_projection_excludes_runtime_fields": [
            "status", "evidence_ids", "artifact_ids", "lock_ids", "attempt_count", "created_sequence",
            "last_state_change_sequence", "disposition_reason",
        ],
        "binding_projection_is_obligation_identity": False,
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "obligation_edges": "EXISTING_AASM_CALCULUS_V1_REQUIRES_EDGES_ONLY",
        "obligation_statuses": sorted(OBLIGATION_STATUSES),
        "obligation_status_machine": "EXISTING_AASM_CALCULUS_V1_OBLIGATION_TRANSITIONS_UNCHANGED",
        "phases": list(OBLIGATION_PHASES),
        "normal_phase_order": list(NORMAL_OBLIGATION_PHASES),
        "recovery_phase_order": "ORTHOGONAL_NO_IMPLICIT_PRECEDENCE",
        "plan_coverage": "EXACTLY_ONE_BINDING_PER_EXISTING_OBLIGATION_FAIL_CLOSED",
        "normal_dependency_order": "REQUIRES_EDGE_CANNOT_POINT_FROM_LATER_NORMAL_PHASE_TO_EARLIER_NORMAL_PHASE",
        "recovery_dependency_order": "EXPLICIT_REQUIRES_EDGE_ONLY_NO_PHASE_INFERENCE",
        "scope_binding": "EXACT_EXISTING_OBLIGATION_SCOPE_ID",
        "revision_binding": "EXACT_PROBLEM_REVISION_ID_AND_FINGERPRINT",
        "readiness_satisfied_statuses": list(SATISFIED_OBLIGATION_STATUSES),
        "terminal_unsatisfied_statuses": list(TERMINAL_UNSATISFIED_OBLIGATION_STATUSES),
        "readiness_role": "BOUNDARY_APPLICABILITY_ASSESSMENT_ONLY_NO_MUTATION_OR_AUTHORIZATION",
        "obligation_mutation": "NONE",
        "phase_activation": "NONE",
        "effect_authorization": "NONE",
        "effect_dispatch": "NONE",
        "recovery_execution": "NONE",
        "current_phase_pointer": "NONE",
        "parallel_obligation_store": "NONE",
        "parallel_obligation_lifecycle": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_dispatcher": "NONE",
        "phase_readiness_grants_fact_authority": False,
        "phase_readiness_grants_effect_authority": False,
        "phase_readiness_accepts_artifact": False,
        "phase_readiness_proves_obligation": False,
        "phase_readiness_mutates_status": False,
        "phase_readiness_executes_recovery": False,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "OBLIGATION_PHASE_CONTRACT_ID",
    "OBLIGATION_PHASE_CONTRACT_VERSION",
    "OBLIGATION_PHASE_BINDING_CONTRACT_ID",
    "OBLIGATION_PHASE_BINDING_CONTRACT_VERSION",
    "OBLIGATION_PHASE_ASSESSMENT_CONTRACT_ID",
    "OBLIGATION_PHASE_ASSESSMENT_CONTRACT_VERSION",
    "OBLIGATION_PHASE_STABILITY",
    "CALCULUS_SUBSTRATE_ID",
    "CALCULUS_STATE_SCHEMA_VERSION",
    "OBLIGATION_BINDING_PROJECTION_ID",
    "OBLIGATION_PHASES",
    "NORMAL_OBLIGATION_PHASES",
    "OBLIGATION_PHASE_READINESS",
    "SATISFIED_OBLIGATION_STATUSES",
    "TERMINAL_UNSATISFIED_OBLIGATION_STATUSES",
    "ObligationPhaseBinding",
    "ObligationPhasePlan",
    "ObligationPhaseAssessment",
    "obligation_binding_projection",
    "obligation_semantic_fingerprint",
    "phase_relation",
    "bind_obligation_phase",
    "validate_obligation_phase_binding",
    "validate_obligation_phase_plan",
    "assess_obligation_phase_readiness",
    "obligation_phase_contract",
]
