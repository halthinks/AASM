from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from .semantic_evolution import ExternalReference
from .semantic_projection import SemanticSubjectRef


SAFETY_ENVELOPE_CONTRACT_ID = "aasm.safety.envelope.v1"
SAFETY_ENVELOPE_CONTRACT_VERSION = "0.1.0"
HYBRID_STATE_CONTRACT_ID = "aasm.hybrid.state.v1"
HYBRID_STATE_CONTRACT_VERSION = "0.1.0"
SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID = "aasm.safety.envelope.assessment.v1"
SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
SAFETY_ENVELOPE_HYBRID_STATE_STABILITY = "FOUNDATION_EXPERIMENTAL"

HYBRID_OBSERVATION_STATUSES = ("OBSERVED", "UNKNOWN")
CONSTRAINT_RELATIONS = (
    "WITHIN",
    "OUTSIDE",
    "OVERLAPS_BOUNDARY",
    "UNKNOWN",
    "UNSUPPORTED",
)
SAFETY_ENVELOPE_ASSESSMENT_STATUSES = (
    "SATISFIED",
    "VIOLATED",
    "INDETERMINATE",
    "MODE_UNCOVERED",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"safety-envelope/hybrid-state {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(
            f"safety-envelope/hybrid-state {name} must be a lowercase 64-hex SHA-256 digest"
        )
    return text


def _uniq(values: Sequence[Any], *, name: str) -> tuple[str, ...]:
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
            "binary floating-point values are forbidden in safety-envelope/hybrid-state portable identity"
        )
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(
        f"safety-envelope/hybrid-state value is not JSON serializable: {type(value)!r}"
    )


def _subject(value: SemanticSubjectRef | Mapping[str, Any]) -> SemanticSubjectRef:
    return value if isinstance(value, SemanticSubjectRef) else SemanticSubjectRef.from_dict(value)


def _external_refs(
    values: Sequence[ExternalReference | Mapping[str, Any]],
) -> tuple[ExternalReference, ...]:
    refs = tuple(
        value if isinstance(value, ExternalReference) else ExternalReference.from_dict(value)
        for value in values
    )
    fingerprints = [ref.fingerprint for ref in refs]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("duplicate external reference in safety-envelope/hybrid-state record")
    for ref in refs:
        _jsonable(ref.identity_payload())
    return tuple(
        sorted(
            refs,
            key=lambda ref: (
                ref.namespace,
                ref.external_id,
                ref.revision,
                ref.role,
                ref.fingerprint,
            ),
        )
    )


def _revision_bound_subject(
    value: SemanticSubjectRef | Mapping[str, Any],
    revision_id: str,
    revision_fingerprint: str,
) -> SemanticSubjectRef:
    subject = _subject(value)
    if subject.revision_bound and (
        subject.revision_id != revision_id
        or subject.revision_fingerprint != revision_fingerprint
    ):
        raise ValueError(
            "safety-envelope/hybrid-state subject revision must match exact problem revision binding"
        )
    return subject


