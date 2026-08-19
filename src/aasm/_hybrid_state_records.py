from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .semantic_evolution import ExternalReference
from .semantic_projection import SemanticSubjectRef
from .semantic_result import semantic_fingerprint
from ._safety_envelope_common import (
    HYBRID_OBSERVATION_STATUSES, HYBRID_STATE_CONTRACT_ID, HYBRID_STATE_CONTRACT_VERSION,
    _external_refs, _jsonable, _optional, _required, _revision_bound_subject, _sha256, _uniq,
)

@dataclass(frozen=True)
class HybridQuantityObservation:
    variable_id: str
    status: str
    quantity_id: str = ""
    quantity_fingerprint: str = ""
    canonical_projection_fingerprint: str = ""
    evidence_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        variable_id = _required("observation variable_id", self.variable_id)
        status = _required("observation status", self.status).upper()
        if status not in HYBRID_OBSERVATION_STATUSES:
            raise ValueError(f"unsupported hybrid observation status: {status}")
        evidence_ids = _uniq(self.evidence_ids, name="observation evidence_id")
        external_references = _external_refs(self.external_references)
        if not evidence_ids and not external_references:
            raise ValueError(
                "hybrid quantity observation requires explicit Evidence or external reference provenance"
            )
        if status == "OBSERVED":
            quantity_id = _required("observation quantity_id", self.quantity_id)
            quantity_fingerprint = _sha256(
                "observation quantity_fingerprint", self.quantity_fingerprint
            )
            projection_fingerprint = _sha256(
                "observation canonical_projection_fingerprint",
                self.canonical_projection_fingerprint,
            )
        else:
            if any(
                _optional(value)
                for value in (
                    self.quantity_id,
                    self.quantity_fingerprint,
                    self.canonical_projection_fingerprint,
                )
            ):
                raise ValueError("UNKNOWN hybrid observation cannot claim a quantity identity")
            quantity_id = ""
            quantity_fingerprint = ""
            projection_fingerprint = ""
        object.__setattr__(self, "variable_id", variable_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "quantity_id", quantity_id)
        object.__setattr__(self, "quantity_fingerprint", quantity_fingerprint)
        object.__setattr__(
            self, "canonical_projection_fingerprint", projection_fingerprint
        )
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "external_references", external_references)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "status": self.status,
            "quantity_id": self.quantity_id,
            "quantity_fingerprint": self.quantity_fingerprint,
            "canonical_projection_fingerprint": self.canonical_projection_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "external_references": [ref.identity_payload() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "external_references": [ref.to_dict() for ref in self.external_references],
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HybridQuantityObservation":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("hybrid quantity observation fingerprint mismatch")
        return item


@dataclass(frozen=True)
class HybridState:
    state_name: str
    subject: SemanticSubjectRef | Mapping[str, Any]
    mode_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    observations: tuple[HybridQuantityObservation | Mapping[str, Any], ...]
    mode_evidence_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    state_id: str = ""
    contract_id: str = HYBRID_STATE_CONTRACT_ID
    contract_version: str = HYBRID_STATE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != HYBRID_STATE_CONTRACT_ID
            or self.contract_version != HYBRID_STATE_CONTRACT_VERSION
        ):
            raise ValueError("unsupported hybrid-state contract")
        state_name = _required("state_name", self.state_name)
        mode_id = _required("mode_id", self.mode_id)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256(
            "problem_revision_fingerprint", self.problem_revision_fingerprint
        )
        subject = _revision_bound_subject(
            self.subject, revision_id, revision_fingerprint
        )
        observations = tuple(
            value
            if isinstance(value, HybridQuantityObservation)
            else HybridQuantityObservation.from_dict(value)
            for value in self.observations
        )
        variable_ids = [value.variable_id for value in observations]
        if len(variable_ids) != len(set(variable_ids)):
            raise ValueError("hybrid state permits exactly one observation per variable_id")
        observations = tuple(sorted(observations, key=lambda value: value.variable_id))
        mode_evidence_ids = _uniq(
            self.mode_evidence_ids, name="mode observation evidence_id"
        )
        external_references = _external_refs(self.external_references)
        if not mode_evidence_ids and not external_references:
            raise ValueError(
                "hybrid state discrete mode requires explicit Evidence or external reference provenance"
            )
        object.__setattr__(self, "state_name", state_name)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "mode_id", mode_id)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "mode_evidence_ids", mode_evidence_ids)
        object.__setattr__(self, "external_references", external_references)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"hybrid-state-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.state_id)
        if supplied and supplied != derived:
            raise ValueError("hybrid state_id does not match canonical identity")
        object.__setattr__(self, "state_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "state_name": self.state_name,
            "subject": self.subject.identity_payload(),
            "mode_id": self.mode_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "observations": [value.identity_payload() for value in self.observations],
            "mode_evidence_ids": list(self.mode_evidence_ids),
            "external_references": [ref.identity_payload() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"state_id": self.state_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "state_name": self.state_name,
            "subject": self.subject.to_dict(),
            "mode_id": self.mode_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "observations": [value.to_dict() for value in self.observations],
            "mode_evidence_ids": list(self.mode_evidence_ids),
            "external_references": [ref.to_dict() for ref in self.external_references],
            "metadata": _jsonable(self.metadata),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HybridState":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["observations"] = tuple(payload.get("observations") or ())
        payload["mode_evidence_ids"] = tuple(payload.get("mode_evidence_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("hybrid state fingerprint mismatch")
        return item


