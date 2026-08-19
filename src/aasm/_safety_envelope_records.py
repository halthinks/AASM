from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .semantic_evolution import ExternalReference
from .semantic_projection import SemanticSubjectRef
from .semantic_result import semantic_fingerprint
from ._safety_envelope_common import (
    SAFETY_ENVELOPE_CONTRACT_ID, SAFETY_ENVELOPE_CONTRACT_VERSION,
    _external_refs, _jsonable, _optional, _required, _revision_bound_subject, _sha256, _uniq,
)

@dataclass(frozen=True)
class SafetyEnvelopeConstraint:
    constraint_id: str
    variable_id: str
    rule_revision_id: str
    rule_fingerprint: str
    allowed_quantity_id: str
    allowed_quantity_fingerprint: str
    allowed_projection_fingerprint: str
    evidence_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "constraint_id",
            "variable_id",
            "rule_revision_id",
            "allowed_quantity_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in (
            "rule_fingerprint",
            "allowed_quantity_fingerprint",
            "allowed_projection_fingerprint",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(
            self,
            "evidence_ids",
            _uniq(self.evidence_ids, name="constraint evidence_id"),
        )
        object.__setattr__(self, "external_references", _external_refs(self.external_references))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "variable_id": self.variable_id,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "allowed_quantity_id": self.allowed_quantity_id,
            "allowed_quantity_fingerprint": self.allowed_quantity_fingerprint,
            "allowed_projection_fingerprint": self.allowed_projection_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.identity_payload() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SafetyEnvelopeConstraint":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("safety envelope constraint fingerprint mismatch")
        return item


@dataclass(frozen=True)
class SafetyModeEnvelope:
    mode_id: str
    constraints: tuple[SafetyEnvelopeConstraint | Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        mode_id = _required("mode_id", self.mode_id)
        constraints = tuple(
            value
            if isinstance(value, SafetyEnvelopeConstraint)
            else SafetyEnvelopeConstraint.from_dict(value)
            for value in self.constraints
        )
        if not constraints:
            raise ValueError("safety mode envelope requires at least one continuous-quantity constraint")
        constraint_ids = [value.constraint_id for value in constraints]
        variable_ids = [value.variable_id for value in constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("safety mode envelope constraint IDs must be unique")
        if len(variable_ids) != len(set(variable_ids)):
            raise ValueError("safety mode envelope permits exactly one constraint per variable_id")
        constraints = tuple(sorted(constraints, key=lambda value: value.constraint_id))
        object.__setattr__(self, "mode_id", mode_id)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(
            self,
            "evidence_ids",
            _uniq(self.evidence_ids, name="mode-envelope evidence_id"),
        )
        object.__setattr__(self, "external_references", _external_refs(self.external_references))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "constraints": [value.identity_payload() for value in self.constraints],
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.identity_payload() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode_id": self.mode_id,
            "constraints": [value.to_dict() for value in self.constraints],
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.to_dict() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SafetyModeEnvelope":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["constraints"] = tuple(payload.get("constraints") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("safety mode envelope fingerprint mismatch")
        return item


@dataclass(frozen=True)
class SafetyEnvelope:
    envelope_name: str
    subject: SemanticSubjectRef | Mapping[str, Any]
    problem_revision_id: str
    problem_revision_fingerprint: str
    modes: tuple[SafetyModeEnvelope | Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    envelope_id: str = ""
    contract_id: str = SAFETY_ENVELOPE_CONTRACT_ID
    contract_version: str = SAFETY_ENVELOPE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != SAFETY_ENVELOPE_CONTRACT_ID
            or self.contract_version != SAFETY_ENVELOPE_CONTRACT_VERSION
        ):
            raise ValueError("unsupported safety-envelope contract")
        name = _required("envelope_name", self.envelope_name)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256(
            "problem_revision_fingerprint", self.problem_revision_fingerprint
        )
        subject = _revision_bound_subject(
            self.subject, revision_id, revision_fingerprint
        )
        modes = tuple(
            value if isinstance(value, SafetyModeEnvelope) else SafetyModeEnvelope.from_dict(value)
            for value in self.modes
        )
        if not modes:
            raise ValueError("safety envelope requires at least one discrete mode envelope")
        mode_ids = [value.mode_id for value in modes]
        if len(mode_ids) != len(set(mode_ids)):
            raise ValueError("safety envelope mode IDs must be unique")
        modes = tuple(sorted(modes, key=lambda value: value.mode_id))
        object.__setattr__(self, "envelope_name", name)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "modes", modes)
        object.__setattr__(
            self,
            "evidence_ids",
            _uniq(self.evidence_ids, name="safety-envelope evidence_id"),
        )
        object.__setattr__(self, "external_references", _external_refs(self.external_references))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"safety-envelope-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.envelope_id)
        if supplied and supplied != derived:
            raise ValueError("safety envelope_id does not match canonical identity")
        object.__setattr__(self, "envelope_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_name": self.envelope_name,
            "subject": self.subject.identity_payload(),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "modes": [value.identity_payload() for value in self.modes],
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.identity_payload() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"envelope_id": self.envelope_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_name": self.envelope_name,
            "subject": self.subject.to_dict(),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "modes": [value.to_dict() for value in self.modes],
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.to_dict() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SafetyEnvelope":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["modes"] = tuple(payload.get("modes") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("safety envelope fingerprint mismatch")
        return item


