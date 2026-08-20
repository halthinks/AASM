from __future__ import annotations

"""S5.5 backend-independent core/conflict semantic contracts.

The pipeline preserves external references through raw -> normalized -> reduced
-> independently rechecked conflict cores.  Claim strength is explicit and may
never be inferred from a smaller-looking set.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import math
import re
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint

CORE_CONFLICT_CONTRACT_ID = "aasm.core-conflict.v1"
CORE_CONFLICT_CONTRACT_VERSION = "0.1.0"
CORE_CONFLICT_STABILITY = "FOUNDATION_EXPERIMENTAL"
CORE_STAGES = ("RAW", "NORMALIZED", "REDUCED", "RECHECKED")
CORE_CLAIM_KINDS = (
    "NONE",
    "BACKEND_REPORTED",
    "CONFLICT_PRESERVING",
    "IRREDUCIBLE",
    "MINIMUM_CARDINALITY",
    "MINIMUM_WEIGHT",
    "BUDGET_LIMITED_PARTIAL",
)
RECHECK_OUTCOMES = ("CONFLICT", "SATISFIABLE", "UNKNOWN", "ERROR")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"core conflict {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"core conflict {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(sorted({_required(name, value) for value in values}))
    if not allow_empty and not items:
        raise ValueError(f"core conflict requires at least one {name}")
    return items


def _portable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(k): _portable(v) for k, v in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_portable(v) for v in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("non-finite floats are forbidden in core conflict identity")
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"core conflict value is not portable JSON: {type(value)!r}")


def _weight(value: float | int | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("core member weight must be finite and non-negative")
    return number


def _round_trip(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


@dataclass(frozen=True)
class CoreMember:
    external_reference_id: str
    normalized_reference_id: str
    reference_kind: str
    source_scope_id: str
    source_fingerprint: str
    weight: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "external_reference_id", _required("external_reference_id", self.external_reference_id))
        object.__setattr__(self, "normalized_reference_id", _required("normalized_reference_id", self.normalized_reference_id))
        object.__setattr__(self, "reference_kind", _required("reference_kind", self.reference_kind).upper())
        object.__setattr__(self, "source_scope_id", _required("source_scope_id", self.source_scope_id))
        object.__setattr__(self, "source_fingerprint", _sha256("source_fingerprint", self.source_fingerprint))
        object.__setattr__(self, "weight", _weight(self.weight))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "external_reference_id": self.external_reference_id,
            "normalized_reference_id": self.normalized_reference_id,
            "reference_kind": self.reference_kind,
            "source_scope_id": self.source_scope_id,
            "source_fingerprint": self.source_fingerprint,
            "weight": self.weight,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CoreMember":
        payload = deepcopy(dict(value)); supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload); _round_trip(item, supplied, label="core member"); return item


@dataclass(frozen=True)
class CoreProvenance:
    problem_revision_id: str
    problem_semantic_fingerprint: str
    solver_backend: str
    solver_backend_version: str
    solver_run_id: str
    solver_evidence_ids: tuple[str, ...]
    external_result_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "problem_revision_id", _required("problem_revision_id", self.problem_revision_id))
        object.__setattr__(self, "problem_semantic_fingerprint", _sha256("problem_semantic_fingerprint", self.problem_semantic_fingerprint))
        object.__setattr__(self, "solver_backend", _required("solver_backend", self.solver_backend))
        object.__setattr__(self, "solver_backend_version", _required("solver_backend_version", self.solver_backend_version))
        object.__setattr__(self, "solver_run_id", _required("solver_run_id", self.solver_run_id))
        object.__setattr__(self, "solver_evidence_ids", _uniq(self.solver_evidence_ids, name="solver evidence_id", allow_empty=False))
        object.__setattr__(self, "external_result_id", _optional(self.external_result_id))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "problem_revision_id": self.problem_revision_id,
            "problem_semantic_fingerprint": self.problem_semantic_fingerprint,
            "solver_backend": self.solver_backend,
            "solver_backend_version": self.solver_backend_version,
            "solver_run_id": self.solver_run_id,
            "solver_evidence_ids": list(self.solver_evidence_ids),
            "external_result_id": self.external_result_id,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CoreProvenance":
        payload = deepcopy(dict(value)); supplied = _optional(payload.pop("fingerprint", "")); payload["solver_evidence_ids"] = tuple(payload.get("solver_evidence_ids") or ())
        item = cls(**payload); _round_trip(item, supplied, label="core provenance"); return item


@dataclass(frozen=True)
class CoreClaim:
    claim_kind: str
    established: bool
    evidence_ids: tuple[str, ...]
    budget_exhausted: bool = False
    objective: Mapping[str, Any] = field(default_factory=dict)
    certificate: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = _required("claim_kind", self.claim_kind).upper()
        if kind not in CORE_CLAIM_KINDS:
            raise ValueError(f"unsupported core claim kind: {kind}")
        object.__setattr__(self, "claim_kind", kind)
        evidence = _uniq(self.evidence_ids, name="claim evidence_id")
        if self.established and kind != "NONE" and not evidence:
            raise ValueError("established core claim requires explicit Evidence")
        if kind == "BUDGET_LIMITED_PARTIAL" and not self.budget_exhausted:
            raise ValueError("budget-limited partial claim must record budget exhaustion")
        if kind == "MINIMUM_WEIGHT" and not self.objective:
            raise ValueError("minimum-weight claim requires an explicit weight objective")
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "objective", _portable(dict(self.objective)))
        object.__setattr__(self, "certificate", _portable(dict(self.certificate)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_kind": self.claim_kind,
            "established": self.established,
            "evidence_ids": list(self.evidence_ids),
            "budget_exhausted": self.budget_exhausted,
            "objective": _portable(self.objective),
            "certificate": _portable(self.certificate),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CoreClaim":
        payload = deepcopy(dict(value)); payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ()); return cls(**payload)


@dataclass(frozen=True)
class ConflictCore:
    provenance: CoreProvenance
    members: tuple[CoreMember, ...]
    stage: str
    claim: CoreClaim
    parent_core_fingerprint: str = ""
    transformation_evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    core_id: str = ""

    def __post_init__(self) -> None:
        stage = _required("stage", self.stage).upper()
        if stage not in CORE_STAGES:
            raise ValueError(f"unsupported core stage: {stage}")
        object.__setattr__(self, "stage", stage)
        members = tuple(sorted(tuple(self.members), key=lambda m: (m.normalized_reference_id, m.external_reference_id, m.fingerprint)))
        if not members:
            raise ValueError("conflict core requires at least one member")
        normalized_ids = [member.normalized_reference_id for member in members]
        if len(normalized_ids) != len(set(normalized_ids)):
            raise ValueError("conflict core normalized_reference_id values must be unique")
        for member in members:
            if member.source_fingerprint != self.provenance.problem_semantic_fingerprint:
                raise ValueError("core member source fingerprint must equal problem semantic fingerprint")
        object.__setattr__(self, "members", members)
        parent = _optional(self.parent_core_fingerprint)
        if stage != "RAW" and not parent:
            raise ValueError("non-RAW core requires parent_core_fingerprint")
        if parent:
            object.__setattr__(self, "parent_core_fingerprint", _sha256("parent_core_fingerprint", parent))
        evidence = _uniq(self.transformation_evidence_ids, name="transformation evidence_id")
        if stage in {"REDUCED", "RECHECKED"} and not evidence:
            raise ValueError(f"{stage} core requires transformation Evidence")
        object.__setattr__(self, "transformation_evidence_ids", evidence)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"conflict-core-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.core_id)
        if supplied and supplied != derived:
            raise ValueError("core_id does not match canonical identity")
        object.__setattr__(self, "core_id", derived)

    @property
    def cardinality(self) -> int:
        return len(self.members)

    @property
    def total_weight(self) -> float | None:
        if any(member.weight is None for member in self.members):
            return None
        return sum(float(member.weight) for member in self.members)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "provenance": self.provenance.to_dict(),
            "members": [member.to_dict() for member in self.members],
            "stage": self.stage,
            "claim": self.claim.to_dict(),
            "parent_core_fingerprint": self.parent_core_fingerprint,
            "transformation_evidence_ids": list(self.transformation_evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"core_id": self.core_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"core_id": self.core_id, **self.identity_payload(), "cardinality": self.cardinality, "total_weight": self.total_weight, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConflictCore":
        payload = deepcopy(dict(value)); supplied = _optional(payload.pop("fingerprint", "")); payload.pop("cardinality", None); payload.pop("total_weight", None)
        payload["provenance"] = CoreProvenance.from_dict(payload["provenance"]); payload["members"] = tuple(CoreMember.from_dict(v) for v in payload.get("members") or ()); payload["claim"] = CoreClaim.from_dict(payload["claim"]); payload["transformation_evidence_ids"] = tuple(payload.get("transformation_evidence_ids") or ())
        item = cls(**payload); _round_trip(item, supplied, label="conflict core"); return item


@dataclass(frozen=True)
class CoreRecheck:
    source_core_fingerprint: str
    problem_semantic_fingerprint: str
    checked_member_ids: tuple[str, ...]
    outcome: str
    verifier_id: str
    evidence_ids: tuple[str, ...]
    independent_from_solver_run: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_core_fingerprint", _sha256("source_core_fingerprint", self.source_core_fingerprint))
        object.__setattr__(self, "problem_semantic_fingerprint", _sha256("problem_semantic_fingerprint", self.problem_semantic_fingerprint))
        object.__setattr__(self, "checked_member_ids", _uniq(self.checked_member_ids, name="checked member_id", allow_empty=False))
        outcome = _required("recheck outcome", self.outcome).upper()
        if outcome not in RECHECK_OUTCOMES:
            raise ValueError(f"unsupported recheck outcome: {outcome}")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "verifier_id", _required("verifier_id", self.verifier_id))
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="recheck evidence_id", allow_empty=False))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_core_fingerprint": self.source_core_fingerprint,
            "problem_semantic_fingerprint": self.problem_semantic_fingerprint,
            "checked_member_ids": list(self.checked_member_ids),
            "outcome": self.outcome,
            "verifier_id": self.verifier_id,
            "evidence_ids": list(self.evidence_ids),
            "independent_from_solver_run": self.independent_from_solver_run,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CoreRecheck":
        payload = deepcopy(dict(value)); supplied = _optional(payload.pop("fingerprint", "")); payload["checked_member_ids"] = tuple(payload.get("checked_member_ids") or ()); payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload); _round_trip(item, supplied, label="core recheck"); return item
