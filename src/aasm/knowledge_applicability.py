from __future__ import annotations

"""S5.4 governed knowledge applicability and application contracts.

Knowledge may be selected because it is relevant, but selection does not prove
that the knowledge applies to the current target and applicability does not
confer authority to apply it. The final application remains separately bound
to the existing AASM authority plane.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import math
import re
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint

KNOWLEDGE_APPLICABILITY_CONTRACT_ID = "aasm.knowledge.applicability.v1"
KNOWLEDGE_APPLICABILITY_CONTRACT_VERSION = "0.1.0"
KNOWLEDGE_APPLICATION_CONTRACT_ID = "aasm.knowledge.application.v1"
KNOWLEDGE_APPLICATION_CONTRACT_VERSION = "0.1.0"
KNOWLEDGE_APPLICABILITY_STABILITY = "FOUNDATION_EXPERIMENTAL"
KNOWLEDGE_APPLICABILITY_STATUSES = ("APPLICABLE", "INAPPLICABLE", "INCONCLUSIVE")
KNOWLEDGE_PREDICATE_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
KNOWLEDGE_VERIFICATION_EFFECTS = ("NONE", "REDUCE", "REPLACE")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"knowledge applicability {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"knowledge applicability {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(sorted({_required(name, value) for value in values}))
    if not allow_empty and not items:
        raise ValueError(f"knowledge applicability requires at least one {name}")
    return items


def _portable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _portable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_portable(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("non-finite floating-point values are forbidden in knowledge portable identity")
        return value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"knowledge applicability value is not portable JSON: {type(value)!r}")


def _confidence(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError("knowledge confidence must be finite in [0, 1]")
    return number


def _freshness(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError("knowledge freshness_seconds must be finite and non-negative")
    return number


def _round_trip_fingerprint(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


@dataclass(frozen=True)
class KnowledgeItem:
    knowledge_kind: str
    content: Any
    source_scope_id: str
    source_object_id: str
    source_fingerprint: str
    applicability_scope_ids: tuple[str, ...]
    applicability_predicates: tuple[str, ...]
    invalidation_triggers: tuple[str, ...]
    source_evidence_ids: tuple[str, ...] = ()
    source_run_id: str = ""
    freshness_seconds: float | None = None
    created_at: float = 0.0
    confidence: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    knowledge_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "knowledge_kind", _required("knowledge_kind", self.knowledge_kind).upper())
        object.__setattr__(self, "content", _portable(self.content))
        object.__setattr__(self, "source_scope_id", _required("source_scope_id", self.source_scope_id))
        object.__setattr__(self, "source_object_id", _required("source_object_id", self.source_object_id))
        object.__setattr__(self, "source_fingerprint", _sha256("source_fingerprint", self.source_fingerprint))
        object.__setattr__(self, "applicability_scope_ids", _uniq(self.applicability_scope_ids, name="applicability scope_id", allow_empty=False))
        object.__setattr__(self, "applicability_predicates", _uniq(self.applicability_predicates, name="applicability predicate", allow_empty=False))
        object.__setattr__(self, "invalidation_triggers", _uniq(self.invalidation_triggers, name="invalidation trigger", allow_empty=False))
        object.__setattr__(self, "source_evidence_ids", _uniq(self.source_evidence_ids, name="source evidence_id"))
        object.__setattr__(self, "source_run_id", _optional(self.source_run_id))
        object.__setattr__(self, "freshness_seconds", _freshness(self.freshness_seconds))
        created = float(self.created_at)
        if not math.isfinite(created) or created < 0.0:
            raise ValueError("knowledge created_at must be finite and non-negative")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"knowledge-item-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.knowledge_id)
        if supplied and supplied != derived:
            raise ValueError("knowledge_id does not match canonical identity")
        object.__setattr__(self, "knowledge_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "knowledge_kind": self.knowledge_kind,
            "content": _portable(self.content),
            "source_scope_id": self.source_scope_id,
            "source_object_id": self.source_object_id,
            "source_fingerprint": self.source_fingerprint,
            "applicability_scope_ids": list(self.applicability_scope_ids),
            "applicability_predicates": list(self.applicability_predicates),
            "invalidation_triggers": list(self.invalidation_triggers),
            "source_evidence_ids": list(self.source_evidence_ids),
            "source_run_id": self.source_run_id,
            "freshness_seconds": self.freshness_seconds,
            "created_at": self.created_at,
            "confidence": self.confidence,
            "metadata": _portable(self.metadata),
            "source_authority_transfer": "NEVER",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"knowledge_id": self.knowledge_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"knowledge_id": self.knowledge_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeItem":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload.pop("source_authority_transfer", None)
        for key in ("applicability_scope_ids", "applicability_predicates", "invalidation_triggers", "source_evidence_ids"):
            payload[key] = tuple(payload.get(key) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="knowledge item")
        return item

    def is_fresh(self, as_of: float) -> bool:
        return self.freshness_seconds is None or float(as_of) <= self.created_at + self.freshness_seconds


@dataclass(frozen=True)
class KnowledgeSelection:
    knowledge_id: str
    knowledge_fingerprint: str
    target_scope_id: str
    target_semantic_fingerprint: str
    selection_basis: str
    selected_by: str
    selection_evidence_ids: tuple[str, ...] = ()
    rank: int | None = None
    confidence: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    selection_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "knowledge_id", _required("knowledge_id", self.knowledge_id))
        object.__setattr__(self, "knowledge_fingerprint", _sha256("knowledge_fingerprint", self.knowledge_fingerprint))
        object.__setattr__(self, "target_scope_id", _required("target_scope_id", self.target_scope_id))
        object.__setattr__(self, "target_semantic_fingerprint", _sha256("target_semantic_fingerprint", self.target_semantic_fingerprint))
        object.__setattr__(self, "selection_basis", _required("selection_basis", self.selection_basis))
        object.__setattr__(self, "selected_by", _required("selected_by", self.selected_by))
        object.__setattr__(self, "selection_evidence_ids", _uniq(self.selection_evidence_ids, name="selection evidence_id"))
        if self.rank is not None:
            rank = int(self.rank)
            if rank < 0:
                raise ValueError("knowledge selection rank must be non-negative")
            object.__setattr__(self, "rank", rank)
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"knowledge-selection-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.selection_id)
        if supplied and supplied != derived:
            raise ValueError("knowledge selection_id does not match canonical identity")
        object.__setattr__(self, "selection_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_fingerprint": self.knowledge_fingerprint,
            "target_scope_id": self.target_scope_id,
            "target_semantic_fingerprint": self.target_semantic_fingerprint,
            "selection_basis": self.selection_basis,
            "selected_by": self.selected_by,
            "selection_evidence_ids": list(self.selection_evidence_ids),
            "rank": self.rank,
            "confidence": self.confidence,
            "metadata": _portable(self.metadata),
            "applicability_claim": "NONE",
            "authority_claim": "NONE",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"selection_id": self.selection_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"selection_id": self.selection_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeSelection":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload.pop("applicability_claim", None)
        payload.pop("authority_claim", None)
        payload["selection_evidence_ids"] = tuple(payload.get("selection_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="knowledge selection")
        return item


@dataclass(frozen=True)
class ApplicabilityPredicateResult:
    predicate: str
    status: str
    rationale: str
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "predicate", _required("predicate", self.predicate))
        status = _required("predicate status", self.status).upper()
        if status not in KNOWLEDGE_PREDICATE_STATUSES:
            raise ValueError(f"unsupported knowledge applicability predicate status: {status}")
        evidence = _uniq(self.evidence_ids, name="predicate evidence_id")
        if status in {"PASS", "FAIL"} and not evidence:
            raise ValueError(f"{status} applicability predicate requires Evidence")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "rationale", _required("predicate rationale", self.rationale))
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {"predicate": self.predicate, "status": self.status, "rationale": self.rationale, "evidence_ids": list(self.evidence_ids), "metadata": _portable(self.metadata)}

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApplicabilityPredicateResult":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="applicability predicate result")
        return item


@dataclass(frozen=True)
class ApplicabilityCheck:
    knowledge_id: str
    knowledge_fingerprint: str
    selection_id: str
    selection_fingerprint: str
    target_scope_id: str
    target_semantic_fingerprint: str
    predicate_results: tuple[ApplicabilityPredicateResult | Mapping[str, Any], ...]
    assessed_by: str
    assessed_at: float
    invalidation_triggers: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    applicability_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "knowledge_id", _required("knowledge_id", self.knowledge_id))
        object.__setattr__(self, "knowledge_fingerprint", _sha256("knowledge_fingerprint", self.knowledge_fingerprint))
        object.__setattr__(self, "selection_id", _required("selection_id", self.selection_id))
        object.__setattr__(self, "selection_fingerprint", _sha256("selection_fingerprint", self.selection_fingerprint))
        object.__setattr__(self, "target_scope_id", _required("target_scope_id", self.target_scope_id))
        object.__setattr__(self, "target_semantic_fingerprint", _sha256("target_semantic_fingerprint", self.target_semantic_fingerprint))
        results = tuple(row if isinstance(row, ApplicabilityPredicateResult) else ApplicabilityPredicateResult.from_dict(row) for row in self.predicate_results)
        if not results:
            raise ValueError("knowledge applicability check requires at least one predicate result")
        predicates = [row.predicate for row in results]
        if len(predicates) != len(set(predicates)):
            raise ValueError("knowledge applicability predicate results must be unique by predicate")
        object.__setattr__(self, "predicate_results", tuple(sorted(results, key=lambda row: row.predicate)))
        object.__setattr__(self, "assessed_by", _required("assessed_by", self.assessed_by))
        assessed = float(self.assessed_at)
        if not math.isfinite(assessed) or assessed < 0.0:
            raise ValueError("knowledge applicability assessed_at must be finite and non-negative")
        object.__setattr__(self, "assessed_at", assessed)
        object.__setattr__(self, "invalidation_triggers", _uniq(self.invalidation_triggers, name="invalidation trigger", allow_empty=False))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"knowledge-applicability-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.applicability_id)
        if supplied and supplied != derived:
            raise ValueError("knowledge applicability_id does not match canonical identity")
        object.__setattr__(self, "applicability_id", derived)

    @property
    def status(self) -> str:
        statuses = {row.status for row in self.predicate_results}
        if "FAIL" in statuses:
            return "INAPPLICABLE"
        if statuses == {"PASS"}:
            return "APPLICABLE"
        return "INCONCLUSIVE"

    @property
    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(sorted({eid for row in self.predicate_results for eid in row.evidence_ids}))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "knowledge_fingerprint": self.knowledge_fingerprint,
            "selection_id": self.selection_id,
            "selection_fingerprint": self.selection_fingerprint,
            "target_scope_id": self.target_scope_id,
            "target_semantic_fingerprint": self.target_semantic_fingerprint,
            "predicate_results": [row.to_dict() for row in self.predicate_results],
            "assessed_by": self.assessed_by,
            "assessed_at": self.assessed_at,
            "invalidation_triggers": list(self.invalidation_triggers),
            "metadata": _portable(self.metadata),
            "status": self.status,
            "authority_claim": "NONE",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"applicability_id": self.applicability_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"applicability_id": self.applicability_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApplicabilityCheck":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        supplied_status = _optional(payload.pop("status", ""))
        payload.pop("authority_claim", None)
        payload["predicate_results"] = tuple(payload.get("predicate_results") or ())
        payload["invalidation_triggers"] = tuple(payload.get("invalidation_triggers") or ())
        item = cls(**payload)
        if supplied_status and supplied_status != item.status:
            raise ValueError("knowledge applicability derived status mismatch")
        _round_trip_fingerprint(item, supplied, label="knowledge applicability")
        return item


@dataclass(frozen=True)
class KnowledgeApplication:
    knowledge_id: str
    knowledge_fingerprint: str
    selection_id: str
    selection_fingerprint: str
    applicability_id: str
    applicability_fingerprint: str
    target_scope_id: str
    target_semantic_fingerprint: str
    application_kind: str
    verification_effect: str
    application_evidence_ids: tuple[str, ...]
    authorization_id: str
    authority: str
    authorized_proposal_fingerprint: str
    authorization_event_id: str
    applied_by: str
    applied_at: float
    metadata: Mapping[str, Any] = field(default_factory=dict)
    application_id: str = ""

    def __post_init__(self) -> None:
        for name in ("knowledge_id", "selection_id", "applicability_id", "authorization_id", "authority", "authorization_event_id", "applied_by"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in ("knowledge_fingerprint", "selection_fingerprint", "applicability_fingerprint", "target_semantic_fingerprint", "authorized_proposal_fingerprint"):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(self, "target_scope_id", _required("target_scope_id", self.target_scope_id))
        object.__setattr__(self, "application_kind", _required("application_kind", self.application_kind).upper())
        effect = _required("verification_effect", self.verification_effect).upper()
        if effect not in KNOWLEDGE_VERIFICATION_EFFECTS:
            raise ValueError(f"unsupported knowledge verification effect: {effect}")
        object.__setattr__(self, "verification_effect", effect)
        object.__setattr__(self, "application_evidence_ids", _uniq(self.application_evidence_ids, name="application evidence_id", allow_empty=False))
        applied = float(self.applied_at)
        if not math.isfinite(applied) or applied < 0.0:
            raise ValueError("knowledge application applied_at must be finite and non-negative")
        object.__setattr__(self, "applied_at", applied)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"knowledge-application-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.application_id)
        if supplied and supplied != derived:
            raise ValueError("knowledge application_id does not match canonical identity")
        object.__setattr__(self, "application_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id, "knowledge_fingerprint": self.knowledge_fingerprint,
            "selection_id": self.selection_id, "selection_fingerprint": self.selection_fingerprint,
            "applicability_id": self.applicability_id, "applicability_fingerprint": self.applicability_fingerprint,
            "target_scope_id": self.target_scope_id, "target_semantic_fingerprint": self.target_semantic_fingerprint,
            "application_kind": self.application_kind, "verification_effect": self.verification_effect,
            "application_evidence_ids": list(self.application_evidence_ids), "authorization_id": self.authorization_id,
            "authority": self.authority, "authorized_proposal_fingerprint": self.authorized_proposal_fingerprint,
            "authorization_event_id": self.authorization_event_id, "applied_by": self.applied_by, "applied_at": self.applied_at,
            "metadata": _portable(self.metadata), "source_authority_inherited": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"application_id": self.application_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"application_id": self.application_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "KnowledgeApplication":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload.pop("source_authority_inherited", None)
        payload["application_evidence_ids"] = tuple(payload.get("application_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="knowledge application")
        return item


def knowledge_item_from_cross_run_envelope(envelope: Any, *, receiving_evidence_ids: Sequence[str] = (), metadata: Mapping[str, Any] | None = None) -> KnowledgeItem:
    from .cross_run_knowledge import CrossRunKnowledgeEnvelope
    row = envelope if isinstance(envelope, CrossRunKnowledgeEnvelope) else CrossRunKnowledgeEnvelope.from_dict(envelope)
    merged = {
        "cross_run_envelope_id": row.envelope_id,
        "cross_run_envelope_fingerprint": row.fingerprint,
        "foreign_source_evidence_ids": list(row.source_evidence_ids),
        "foreign_source_artifact_ids": list(row.source_artifact_ids),
        "foreign_source_fingerprints": dict(row.source_fingerprints),
        "foreign_source_authority_provenance": deepcopy(row.source_authority_provenance),
        "foreign_dependency_fingerprints": list(row.dependency_fingerprints),
        "foreign_environment_fingerprint": row.environment_fingerprint,
        "foreign_verification_strength": row.verification_strength,
        "source_authority_transfer": "NEVER",
        **dict(metadata or {}),
    }
    triggers = {"SOURCE_REVOCATION", "SOURCE_SUPERSESSION", "TARGET_SEMANTIC_CHANGE"}
    if row.environment_fingerprint: triggers.add("ENVIRONMENT_CHANGE")
    if row.dependency_fingerprints: triggers.add("DEPENDENCY_CHANGE")
    if row.freshness_seconds is not None: triggers.add("FRESHNESS_EXPIRY")
    return KnowledgeItem(row.knowledge_kind, row.content, row.source_scope_id, row.envelope_id, row.fingerprint, row.applicability_scope_ids, ("cross_run_admission",), tuple(sorted(triggers)), tuple(receiving_evidence_ids), row.source_run_id, row.freshness_seconds, row.created_at, None, merged)


def applicability_check_from_cross_run_certificate(item: KnowledgeItem, selection: KnowledgeSelection, certificate: Any, *, evidence_ids: Sequence[str], assessed_at: float) -> ApplicabilityCheck:
    from .cross_run_knowledge import CrossRunAdmissionCertificate
    if isinstance(certificate, CrossRunAdmissionCertificate):
        cert = certificate
    else:
        payload = deepcopy(dict(certificate))
        payload.pop("fingerprint", None)
        payload.pop("authority_inherited", None)
        payload["reasons"] = tuple(payload.get("reasons") or ())
        cert = CrossRunAdmissionCertificate(**payload)
    if cert.envelope_id != item.source_object_id or cert.envelope_fingerprint != item.source_fingerprint:
        raise ValueError("cross-run admission certificate does not bind the KnowledgeItem source envelope")
    result = ApplicabilityPredicateResult("cross_run_admission", "PASS" if cert.valid else "FAIL", "existing v0.48 receiving-run admission certificate accepted" if cert.valid else "existing v0.48 receiving-run admission certificate rejected", tuple(evidence_ids), {"certificate_id": cert.certificate_id, "certificate_checks": cert.checks, "certificate_reasons": list(cert.reasons)})
    return ApplicabilityCheck(item.knowledge_id, item.fingerprint, selection.selection_id, selection.fingerprint, selection.target_scope_id, selection.target_semantic_fingerprint, (result,), cert.validator_id, assessed_at, item.invalidation_triggers, {"cross_run_certificate_id": cert.certificate_id, "source_authority_inherited": False})


def knowledge_applicability_contract() -> dict[str, Any]:
    return {
        "contract_id": KNOWLEDGE_APPLICABILITY_CONTRACT_ID, "contract_version": KNOWLEDGE_APPLICABILITY_CONTRACT_VERSION,
        "application_contract_id": KNOWLEDGE_APPLICATION_CONTRACT_ID, "application_contract_version": KNOWLEDGE_APPLICATION_CONTRACT_VERSION,
        "stability": KNOWLEDGE_APPLICABILITY_STABILITY,
        "stage_order": ["KnowledgeItem", "KnowledgeSelection", "ApplicabilityCheck", "KnowledgeApplication"],
        "stage_separation": "selected != applicable != applied",
        "selection": "RETRIEVAL_OR_RANKING_ONLY_NOT_APPLICABILITY",
        "applicability": "EXPLICIT_PREDICATES_AND_EVIDENCE_REQUIRED",
        "applicability_statuses": list(KNOWLEDGE_APPLICABILITY_STATUSES),
        "application": "SEPARATE_EXISTING_AASM_AUTHORITY_REQUIRED",
        "source_authority_transfer": "NEVER", "target_binding": "EXACT_SCOPE_AND_SEMANTIC_FINGERPRINT",
        "freshness": "EXPLICIT_AND_FAIL_CLOSED_WHEN_DECLARED", "invalidation": "EXPLICIT_TRIGGERS_PLUS_EVIDENCE_LIFECYCLE",
        "verification_effect_default": "NONE", "verification_relief": "REQUIRES_APPLICABLE_CHECK_PLUS_EXISTING_AASM_AUTHORITY",
        "verification_mutation": "NONE_IN_S5_4",
        "cross_run_compatibility": "V0_48_ENVELOPE_AND_ADMISSION_CERTIFICATE_ADAPTERS_SOURCE_AUTHORITY_NEVER_TRANSFERS",
        "parallel_authority_plane": "NONE",
    }


__all__ = ["KNOWLEDGE_APPLICABILITY_CONTRACT_ID", "KNOWLEDGE_APPLICABILITY_CONTRACT_VERSION", "KNOWLEDGE_APPLICATION_CONTRACT_ID", "KNOWLEDGE_APPLICATION_CONTRACT_VERSION", "KNOWLEDGE_APPLICABILITY_STABILITY", "KNOWLEDGE_APPLICABILITY_STATUSES", "KNOWLEDGE_PREDICATE_STATUSES", "KNOWLEDGE_VERIFICATION_EFFECTS", "KnowledgeItem", "KnowledgeSelection", "ApplicabilityPredicateResult", "ApplicabilityCheck", "KnowledgeApplication", "knowledge_item_from_cross_run_envelope", "applicability_check_from_cross_run_certificate", "knowledge_applicability_contract"]
