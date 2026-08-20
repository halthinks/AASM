from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping

from .calculus import OBLIGATION_STATUSES, content_hash, normalize_calculus_state
from .obligation_phase import (
    OBLIGATION_PHASES,
    ObligationPhasePlan,
    obligation_semantic_fingerprint,
    validate_obligation_phase_plan,
)
from .scopes import scope_id_from
from .semantic_result import semantic_fingerprint


EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"
EPISTEMIC_DEBT_CONTRACT_VERSION = "0.1.0"
EPISTEMIC_DEBT_STABILITY = "FOUNDATION_EXPERIMENTAL"
EPISTEMIC_DEBT_CLASSES = ("OUTSTANDING", "TERMINAL_UNRESOLVED")
SATISFIED_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
TERMINAL_UNRESOLVED_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"epistemic-debt {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(
            f"epistemic-debt {name} must be a lowercase 64-hex SHA-256 digest"
        )
    return text


def _uniq(values: Any, *, name: str) -> tuple[str, ...]:
    return tuple(sorted({_required(name, value) for value in values}))


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
        raise TypeError(
            "binary floating-point values are forbidden in epistemic-debt portable identity"
        )
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"epistemic-debt value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class EpistemicDebtItem:
    obligation_id: str
    obligation_semantic_fingerprint: str
    obligation_status: str
    classification: str
    statement: str
    dependency_obligation_ids: tuple[str, ...] = ()
    required_evidence_types: tuple[str, ...] = ()
    attached_evidence_ids: tuple[str, ...] = ()
    mandatory: bool = True
    persistent: bool = True
    scope_id: str = "root"
    phase: str = ""
    diagnostics: tuple[str, ...] = ()
    item_id: str = ""

    def __post_init__(self) -> None:
        obligation_id = _required("obligation_id", self.obligation_id)
        obligation_fingerprint = _sha256(
            "obligation_semantic_fingerprint",
            self.obligation_semantic_fingerprint,
        )
        status = _required("obligation_status", self.obligation_status).upper()
        if status not in OBLIGATION_STATUSES:
            raise ValueError(f"unsupported existing obligation status: {status}")
        if status in SATISFIED_OBLIGATION_STATUSES:
            raise ValueError("satisfied obligations cannot appear in epistemic debt")
        classification = _required("classification", self.classification).upper()
        if classification not in EPISTEMIC_DEBT_CLASSES:
            raise ValueError(
                f"unsupported epistemic debt classification: {classification}"
            )
        expected = (
            "TERMINAL_UNRESOLVED"
            if status in TERMINAL_UNRESOLVED_STATUSES
            else "OUTSTANDING"
        )
        if classification != expected:
            raise ValueError(
                "epistemic debt classification must be derived from the existing obligation status"
            )
        phase = _optional(self.phase).upper()
        if phase and phase not in OBLIGATION_PHASES:
            raise ValueError(
                f"unsupported obligation phase on epistemic debt item: {phase}"
            )
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(
            self,
            "obligation_semantic_fingerprint",
            obligation_fingerprint,
        )
        object.__setattr__(self, "obligation_status", status)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "statement", _required("statement", self.statement))
        object.__setattr__(
            self,
            "dependency_obligation_ids",
            _uniq(
                self.dependency_obligation_ids,
                name="dependency obligation_id",
            ),
        )
        object.__setattr__(
            self,
            "required_evidence_types",
            _uniq(self.required_evidence_types, name="required evidence type"),
        )
        object.__setattr__(
            self,
            "attached_evidence_ids",
            _uniq(self.attached_evidence_ids, name="attached evidence_id"),
        )
        object.__setattr__(self, "mandatory", bool(self.mandatory))
        object.__setattr__(self, "persistent", bool(self.persistent))
        object.__setattr__(self, "scope_id", _required("scope_id", self.scope_id))
        object.__setattr__(self, "phase", phase)
        object.__setattr__(
            self,
            "diagnostics",
            _uniq(self.diagnostics, name="debt diagnostic"),
        )
        derived = (
            f"epistemic-debt-item-{semantic_fingerprint(self.identity_payload())[:24]}"
        )
        supplied = _optional(self.item_id)
        if supplied and supplied != derived:
            raise ValueError("epistemic debt item_id does not match canonical identity")
        object.__setattr__(self, "item_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "obligation_status": self.obligation_status,
            "classification": self.classification,
            "statement": self.statement,
            "dependency_obligation_ids": list(self.dependency_obligation_ids),
            "required_evidence_types": list(self.required_evidence_types),
            "attached_evidence_ids": list(self.attached_evidence_ids),
            "mandatory": self.mandatory,
            "persistent": self.persistent,
            "scope_id": self.scope_id,
            "phase": self.phase,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            {"item_id": self.item_id, **self.identity_payload()}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicDebtItem":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        for name in (
            "dependency_obligation_ids",
            "required_evidence_types",
            "attached_evidence_ids",
            "diagnostics",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("epistemic debt item fingerprint mismatch")
        return item


@dataclass(frozen=True)
class EpistemicDebtProjection:
    problem_revision_id: str
    problem_revision_fingerprint: str
    calculus_state_fingerprint: str
    items: tuple[EpistemicDebtItem | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    projection_id: str = ""
    contract_id: str = EPISTEMIC_DEBT_CONTRACT_ID
    contract_version: str = EPISTEMIC_DEBT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != EPISTEMIC_DEBT_CONTRACT_ID
            or self.contract_version != EPISTEMIC_DEBT_CONTRACT_VERSION
        ):
            raise ValueError("unsupported epistemic-debt contract")
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256(
            "problem_revision_fingerprint",
            self.problem_revision_fingerprint,
        )
        state_fingerprint = _sha256(
            "calculus_state_fingerprint",
            self.calculus_state_fingerprint,
        )
        items = tuple(
            value
            if isinstance(value, EpistemicDebtItem)
            else EpistemicDebtItem.from_dict(value)
            for value in self.items
        )
        ids = [value.obligation_id for value in items]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "epistemic debt projection permits at most one item per existing obligation_id"
            )
        items = tuple(sorted(items, key=lambda value: value.obligation_id))
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(
            self,
            "problem_revision_fingerprint",
            revision_fingerprint,
        )
        object.__setattr__(self, "calculus_state_fingerprint", state_fingerprint)
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"epistemic-debt-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.projection_id)
        if supplied and supplied != derived:
            raise ValueError(
                "epistemic debt projection_id does not match canonical identity"
            )
        object.__setattr__(self, "projection_id", derived)

    @property
    def outstanding_count(self) -> int:
        return sum(value.classification == "OUTSTANDING" for value in self.items)

    @property
    def terminal_unresolved_count(self) -> int:
        return sum(
            value.classification == "TERMINAL_UNRESOLVED" for value in self.items
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "calculus_state_fingerprint": self.calculus_state_fingerprint,
            "items": [value.identity_payload() for value in self.items],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            {"projection_id": self.projection_id, **self.identity_payload()}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "calculus_state_fingerprint": self.calculus_state_fingerprint,
            "items": [value.to_dict() for value in self.items],
            "total_debt_count": len(self.items),
            "outstanding_count": self.outstanding_count,
            "terminal_unresolved_count": self.terminal_unresolved_count,
            "metadata": _jsonable(self.metadata),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicDebtProjection":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload.pop("total_debt_count", None)
        payload.pop("outstanding_count", None)
        payload.pop("terminal_unresolved_count", None)
        payload["items"] = tuple(payload.get("items") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("epistemic debt projection fingerprint mismatch")
        return item


def _validate_canonical_edges(state: Mapping[str, Any]) -> None:
    obligations = dict(state.get("obligations") or {})
    expected = {
        (str(dependency), str(obligation_id), "REQUIRES")
        for obligation_id, obligation in obligations.items()
        for dependency in obligation.get("dependencies", [])
    }
    actual: set[tuple[str, str, str]] = set()
    for raw in state.get("obligation_edges", []):
        edge = dict(raw)
        src = _required("obligation edge src", edge.get("src"))
        dst = _required("obligation edge dst", edge.get("dst"))
        relation = _required("obligation edge relation", edge.get("relation"))
        if src not in obligations or dst not in obligations:
            raise ValueError(
                "epistemic debt projection encountered an edge with unknown canonical obligation"
            )
        key = (src, dst, relation)
        if key in actual:
            raise ValueError(
                "epistemic debt projection encountered duplicate canonical obligation edge"
            )
        actual.add(key)
    if actual != expected:
        raise ValueError(
            "canonical obligation_edges must exactly represent ObligationRecord.dependencies before epistemic debt projection"
        )


def project_epistemic_debt(
    calculus_state: Mapping[str, Any],
    *,
    problem_revision_id: str,
    problem_revision_fingerprint: str,
    phase_plan: ObligationPhasePlan | Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EpistemicDebtProjection:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    if int(state.get("schema_version", -1)) != 1:
        raise ValueError(
            "epistemic debt projection requires the existing calculus state schema_version 1"
        )
    _validate_canonical_edges(state)
    revision_id = _required("problem_revision_id", problem_revision_id)
    revision_fingerprint = _sha256(
        "problem_revision_fingerprint",
        problem_revision_fingerprint,
    )
    phases: dict[str, str] = {}
    if phase_plan is not None:
        plan = (
            phase_plan
            if isinstance(phase_plan, ObligationPhasePlan)
            else ObligationPhasePlan.from_dict(phase_plan)
        )
        if (
            plan.problem_revision_id != revision_id
            or plan.problem_revision_fingerprint != revision_fingerprint
        ):
            raise ValueError(
                "epistemic debt projection requires the exact obligation-phase ProblemRevision"
            )
        validate_obligation_phase_plan(state, plan)
        phases = {binding.obligation_id: binding.phase for binding in plan.bindings}

    items: list[EpistemicDebtItem] = []
    for obligation_id, row in sorted((state.get("obligations") or {}).items()):
        status = str(row.get("status") or "AVAILABLE").upper()
        if status in SATISFIED_OBLIGATION_STATUSES:
            continue
        classification = (
            "TERMINAL_UNRESOLVED"
            if status in TERMINAL_UNRESOLVED_STATUSES
            else "OUTSTANDING"
        )
        diagnostic = (
            f"TERMINAL_UNRESOLVED:{status}"
            if classification == "TERMINAL_UNRESOLVED"
            else f"OUTSTANDING_STATUS:{status}"
        )
        items.append(
            EpistemicDebtItem(
                obligation_id=obligation_id,
                obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
                obligation_status=status,
                classification=classification,
                statement=str(row.get("statement") or ""),
                dependency_obligation_ids=tuple(row.get("dependencies") or ()),
                required_evidence_types=tuple(row.get("required_evidence_types") or ()),
                attached_evidence_ids=tuple(row.get("evidence_ids") or ()),
                mandatory=bool(row.get("mandatory", True)),
                persistent=bool(row.get("persistent", True)),
                scope_id=scope_id_from(row),
                phase=phases.get(obligation_id, ""),
                diagnostics=(diagnostic,),
            )
        )
    return EpistemicDebtProjection(
        problem_revision_id=revision_id,
        problem_revision_fingerprint=revision_fingerprint,
        calculus_state_fingerprint=content_hash(state),
        items=tuple(items),
        metadata=dict(metadata or {}),
    )


def validate_epistemic_debt_projection(
    calculus_state: Mapping[str, Any],
    projection: EpistemicDebtProjection | Mapping[str, Any],
    *,
    phase_plan: ObligationPhasePlan | Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = (
        projection
        if isinstance(projection, EpistemicDebtProjection)
        else EpistemicDebtProjection.from_dict(projection)
    )
    expected = project_epistemic_debt(
        calculus_state,
        problem_revision_id=item.problem_revision_id,
        problem_revision_fingerprint=item.problem_revision_fingerprint,
        phase_plan=phase_plan,
        metadata=item.metadata,
    )
    if item != expected:
        raise ValueError(
            "epistemic debt projection is stale or mismatched for the exact existing obligation graph"
        )
    return {
        "valid": True,
        "projection_id": item.projection_id,
        "projection_fingerprint": item.fingerprint,
        "calculus_state_fingerprint": item.calculus_state_fingerprint,
        "total_debt_count": len(item.items),
        "outstanding_count": item.outstanding_count,
        "terminal_unresolved_count": item.terminal_unresolved_count,
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "EPISTEMIC_DEBT_CONTRACT_ID",
    "EPISTEMIC_DEBT_CONTRACT_VERSION",
    "EPISTEMIC_DEBT_STABILITY",
    "EPISTEMIC_DEBT_CLASSES",
    "SATISFIED_OBLIGATION_STATUSES",
    "TERMINAL_UNRESOLVED_STATUSES",
    "EpistemicDebtItem",
    "EpistemicDebtProjection",
    "project_epistemic_debt",
    "validate_epistemic_debt_projection",
]
