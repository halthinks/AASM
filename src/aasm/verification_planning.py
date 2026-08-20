from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping, Sequence

from .calculus import OBLIGATION_STATUSES, content_hash, normalize_calculus_state
from .obligation_phase import obligation_semantic_fingerprint
from .semantic_result import semantic_fingerprint
from .typed_protocol import CapabilityContract, VERIFICATION_STRENGTHS


VERIFICATION_PLAN_CONTRACT_ID = "aasm.verification.plan.v1"
VERIFICATION_PLAN_CONTRACT_VERSION = "0.1.0"
VERIFICATION_DEBT_CONTRACT_ID = "aasm.verification.debt.v1"
VERIFICATION_DEBT_CONTRACT_VERSION = "0.1.0"
VERIFICATION_PLANNING_STABILITY = "FOUNDATION_EXPERIMENTAL"

VERIFICATION_FIDELITIES = ("EXACT", "BOUNDED", "APPROXIMATE", "EMPIRICAL", "UNKNOWN")
VERIFICATION_PROPERTY_CLAIM_KINDS = ("SOUNDNESS", "COMPLETENESS")
VERIFICATION_PROPERTY_CLAIM_STATUSES = ("DECLARED", "EVIDENCE_BACKED", "UNKNOWN", "NOT_APPLICABLE")
VERIFICATION_REFERENCE_KINDS = ("ENVIRONMENT", "NUMERICAL_POLICY", "RESOURCE_DEMAND")
VERIFICATION_CACHE_REUSE_ELIGIBILITY = ("FORBIDDEN", "PERFORMANCE_ONLY", "SEMANTIC_IF_CERTIFIED")
VERIFICATION_EVIDENCE_APPLICABILITY_STATUSES = ("APPLICABLE", "INAPPLICABLE", "INDETERMINATE")
VERIFICATION_DEBT_CLASSIFICATIONS = ("UNVERIFIED", "TERMINAL_UNVERIFIED")
VERIFICATION_DEBT_REASONS = (
    "NO_VERIFIER_ASSIGNMENT",
    "NO_ATTACHED_EVIDENCE",
    "EVIDENCE_APPLICABILITY_UNASSESSED",
    "EVIDENCE_TYPE_UNSATISFIED",
    "EVIDENCE_FIDELITY_UNSATISFIED",
    "EVIDENCE_GRADE_UNSATISFIED",
    "ENVIRONMENT_MISMATCH",
    "NUMERICAL_POLICY_MISMATCH",
    "VERIFICATION_STRENGTH_UNSATISFIED",
    "STALE_EVIDENCE",
    "INDETERMINATE_APPLICABILITY",
    "TERMINAL_UNRESOLVED",
)
SATISFIED_VERIFICATION_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
TERMINAL_UNRESOLVED_OBLIGATION_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"verification-planning {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"verification-planning {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Iterable[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(sorted({_required(name, value) for value in values}))
    if not allow_empty and not items:
        raise ValueError(f"verification-planning requires at least one {name}")
    return items


def _portable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _portable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_portable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in verification-planning portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"verification-planning value is not portable JSON: {type(value)!r}")


def _round_trip_fingerprint(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


def _canonical_obligation(row: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(row))
    obligation_id = _required("obligation_id", value.get("obligation_id"))
    status = _required("obligation status", value.get("status", "AVAILABLE")).upper()
    if status not in OBLIGATION_STATUSES:
        raise ValueError(f"unsupported existing obligation status: {status}")
    value["obligation_id"] = obligation_id
    value["status"] = status
    value["required_evidence_types"] = sorted({str(item) for item in value.get("required_evidence_types", [])})
    value["evidence_ids"] = sorted({str(item) for item in value.get("evidence_ids", [])})
    return value


def _verification_obligations(calculus_state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    if int(state.get("schema_version", -1)) != 1:
        raise ValueError("verification planning requires existing calculus state schema_version 1")
    out: dict[str, dict[str, Any]] = {}
    for obligation_id, raw in sorted((state.get("obligations") or {}).items()):
        row = _canonical_obligation(raw)
        if row["status"] in SATISFIED_VERIFICATION_OBLIGATION_STATUSES:
            continue
        if not row["required_evidence_types"]:
            continue
        out[str(obligation_id)] = row
    return out


@dataclass(frozen=True)
class VerificationBoundReference:
    reference_kind: str
    contract_id: str
    object_id: str
    object_fingerprint: str
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = _required("reference_kind", self.reference_kind).upper()
        if kind not in VERIFICATION_REFERENCE_KINDS:
            raise ValueError(f"unsupported verification bound reference kind: {kind}")
        object.__setattr__(self, "reference_kind", kind)
        object.__setattr__(self, "contract_id", _required("reference contract_id", self.contract_id))
        object.__setattr__(self, "object_id", _required("reference object_id", self.object_id))
        object.__setattr__(self, "object_fingerprint", _sha256("reference object_fingerprint", self.object_fingerprint))
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="reference evidence_id"))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "reference_kind": self.reference_kind,
            "contract_id": self.contract_id,
            "object_id": self.object_id,
            "object_fingerprint": self.object_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationBoundReference":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification bound reference")
        return item


@dataclass(frozen=True)
class VerificationPropertyClaim:
    claim_kind: str
    status: str
    statement: str
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = _required("property claim_kind", self.claim_kind).upper()
        status = _required("property claim status", self.status).upper()
        if kind not in VERIFICATION_PROPERTY_CLAIM_KINDS:
            raise ValueError(f"unsupported verifier property claim kind: {kind}")
        if status not in VERIFICATION_PROPERTY_CLAIM_STATUSES:
            raise ValueError(f"unsupported verifier property claim status: {status}")
        statement = _required("property claim statement", self.statement)
        evidence = _uniq(self.evidence_ids, name="property claim evidence_id")
        if status == "EVIDENCE_BACKED" and not evidence:
            raise ValueError("EVIDENCE_BACKED verifier property claim requires Evidence")
        if status in {"UNKNOWN", "NOT_APPLICABLE"} and evidence:
            raise ValueError(f"{status} verifier property claim cannot carry proof-like Evidence")
        object.__setattr__(self, "claim_kind", kind)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "statement", statement)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "claim_kind": self.claim_kind,
            "status": self.status,
            "statement": self.statement,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationPropertyClaim":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification property claim")
        return item


@dataclass(frozen=True)
class VerifierCapabilityProfile:
    verifier_id: str
    capability: CapabilityContract | Mapping[str, Any]
    fidelity: str
    evidence_grade: str
    references: tuple[VerificationBoundReference | Mapping[str, Any], ...]
    soundness_claim: VerificationPropertyClaim | Mapping[str, Any]
    completeness_claim: VerificationPropertyClaim | Mapping[str, Any]
    verification_strengths: tuple[str, ...] = ()
    cache_reuse_eligibility: str = "FORBIDDEN"
    supporting_evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    profile_id: str = ""

    def __post_init__(self) -> None:
        verifier_id = _required("verifier_id", self.verifier_id)
        capability = self.capability if isinstance(self.capability, CapabilityContract) else CapabilityContract.from_dict(self.capability)
        if capability.capability_type != "VERIFIER":
            raise ValueError("verification plan profile requires existing VERIFIER CapabilityContract")
        fidelity = _required("verifier fidelity", self.fidelity).upper()
        if fidelity not in VERIFICATION_FIDELITIES:
            raise ValueError(f"unsupported verifier fidelity: {fidelity}")
        evidence_grade = _required("verifier evidence_grade", self.evidence_grade)
        references = tuple(
            row if isinstance(row, VerificationBoundReference) else VerificationBoundReference.from_dict(row)
            for row in self.references
        )
        by_kind = {kind: [row for row in references if row.reference_kind == kind] for kind in VERIFICATION_REFERENCE_KINDS}
        if len(by_kind["ENVIRONMENT"]) != 1:
            raise ValueError("verifier profile requires exactly one existing ENVIRONMENT reference")
        if len(by_kind["NUMERICAL_POLICY"]) != 1:
            raise ValueError("verifier profile requires exactly one existing NUMERICAL_POLICY reference")
        if not by_kind["RESOURCE_DEMAND"]:
            raise ValueError("verifier profile requires at least one existing RESOURCE_DEMAND reference")
        keys = [(row.reference_kind, row.object_id, row.object_fingerprint) for row in references]
        if len(keys) != len(set(keys)):
            raise ValueError("verifier profile bound references must be unique")
        references = tuple(sorted(references, key=lambda row: (row.reference_kind, row.object_id, row.fingerprint)))
        soundness = self.soundness_claim if isinstance(self.soundness_claim, VerificationPropertyClaim) else VerificationPropertyClaim.from_dict(self.soundness_claim)
        completeness = self.completeness_claim if isinstance(self.completeness_claim, VerificationPropertyClaim) else VerificationPropertyClaim.from_dict(self.completeness_claim)
        if soundness.claim_kind != "SOUNDNESS" or completeness.claim_kind != "COMPLETENESS":
            raise ValueError("verifier profile requires SOUNDNESS and COMPLETENESS claim slots")
        strengths = _uniq(self.verification_strengths, name="verification strength")
        unknown = sorted(set(strengths) - set(VERIFICATION_STRENGTHS))
        if unknown:
            raise ValueError(f"verifier profile declares unsupported verification strengths: {unknown}")
        cache = _required("cache_reuse_eligibility", self.cache_reuse_eligibility).upper()
        if cache not in VERIFICATION_CACHE_REUSE_ELIGIBILITY:
            raise ValueError(f"unsupported verifier cache/reuse eligibility: {cache}")
        support = _uniq(self.supporting_evidence_ids, name="verifier profile supporting evidence_id")
        object.__setattr__(self, "verifier_id", verifier_id)
        object.__setattr__(self, "capability", capability)
        object.__setattr__(self, "fidelity", fidelity)
        object.__setattr__(self, "evidence_grade", evidence_grade)
        object.__setattr__(self, "references", references)
        object.__setattr__(self, "soundness_claim", soundness)
        object.__setattr__(self, "completeness_claim", completeness)
        object.__setattr__(self, "verification_strengths", strengths)
        object.__setattr__(self, "cache_reuse_eligibility", cache)
        object.__setattr__(self, "supporting_evidence_ids", support)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verifier-profile-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.profile_id)
        if supplied and supplied != derived:
            raise ValueError("verifier profile_id does not match canonical identity")
        object.__setattr__(self, "profile_id", derived)

    @property
    def environment_reference(self) -> VerificationBoundReference:
        return next(row for row in self.references if row.reference_kind == "ENVIRONMENT")

    @property
    def numerical_policy_reference(self) -> VerificationBoundReference:
        return next(row for row in self.references if row.reference_kind == "NUMERICAL_POLICY")

    @property
    def resource_demand_references(self) -> tuple[VerificationBoundReference, ...]:
        return tuple(row for row in self.references if row.reference_kind == "RESOURCE_DEMAND")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "verifier_id": self.verifier_id,
            "capability": self.capability.to_dict(),
            "fidelity": self.fidelity,
            "evidence_grade": self.evidence_grade,
            "references": [row.to_dict() for row in self.references],
            "soundness_claim": self.soundness_claim.to_dict(),
            "completeness_claim": self.completeness_claim.to_dict(),
            "verification_strengths": list(self.verification_strengths),
            "cache_reuse_eligibility": self.cache_reuse_eligibility,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"profile_id": self.profile_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"profile_id": self.profile_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerifierCapabilityProfile":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["references"] = tuple(payload.get("references") or ())
        payload["verification_strengths"] = tuple(payload.get("verification_strengths") or ())
        payload["supporting_evidence_ids"] = tuple(payload.get("supporting_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verifier capability profile")
        return item


@dataclass(frozen=True)
class VerificationRequirement:
    obligation_id: str
    obligation_semantic_fingerprint: str
    required_evidence_types: tuple[str, ...]
    acceptable_fidelities: tuple[str, ...]
    acceptable_evidence_grades: tuple[str, ...]
    acceptable_verification_strengths: tuple[str, ...] = ()
    required_environment_id: str = ""
    required_environment_fingerprint: str = ""
    required_numerical_policy_id: str = ""
    required_numerical_policy_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    requirement_id: str = ""

    def __post_init__(self) -> None:
        obligation_id = _required("requirement obligation_id", self.obligation_id)
        obligation_fingerprint = _sha256("requirement obligation_semantic_fingerprint", self.obligation_semantic_fingerprint)
        evidence_types = _uniq(self.required_evidence_types, name="required evidence type", allow_empty=False)
        fidelities = _uniq(self.acceptable_fidelities, name="acceptable fidelity", allow_empty=False)
        unknown_fidelity = sorted(set(fidelities) - set(VERIFICATION_FIDELITIES))
        if unknown_fidelity:
            raise ValueError(f"verification requirement has unsupported fidelities: {unknown_fidelity}")
        grades = _uniq(self.acceptable_evidence_grades, name="acceptable evidence grade", allow_empty=False)
        strengths = _uniq(self.acceptable_verification_strengths, name="acceptable verification strength")
        unknown_strength = sorted(set(strengths) - set(VERIFICATION_STRENGTHS))
        if unknown_strength:
            raise ValueError(f"verification requirement has unsupported strengths: {unknown_strength}")
        environment_id = _optional(self.required_environment_id)
        environment_fingerprint = _optional(self.required_environment_fingerprint).lower()
        if bool(environment_id) != bool(environment_fingerprint):
            raise ValueError("verification requirement environment id/fingerprint must be supplied together")
        if environment_fingerprint:
            environment_fingerprint = _sha256("required_environment_fingerprint", environment_fingerprint)
        numerical_id = _optional(self.required_numerical_policy_id)
        numerical_fingerprint = _optional(self.required_numerical_policy_fingerprint).lower()
        if bool(numerical_id) != bool(numerical_fingerprint):
            raise ValueError("verification requirement numerical-policy id/fingerprint must be supplied together")
        if numerical_fingerprint:
            numerical_fingerprint = _sha256("required_numerical_policy_fingerprint", numerical_fingerprint)
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "obligation_semantic_fingerprint", obligation_fingerprint)
        object.__setattr__(self, "required_evidence_types", evidence_types)
        object.__setattr__(self, "acceptable_fidelities", fidelities)
        object.__setattr__(self, "acceptable_evidence_grades", grades)
        object.__setattr__(self, "acceptable_verification_strengths", strengths)
        object.__setattr__(self, "required_environment_id", environment_id)
        object.__setattr__(self, "required_environment_fingerprint", environment_fingerprint)
        object.__setattr__(self, "required_numerical_policy_id", numerical_id)
        object.__setattr__(self, "required_numerical_policy_fingerprint", numerical_fingerprint)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verification-requirement-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.requirement_id)
        if supplied and supplied != derived:
            raise ValueError("verification requirement_id does not match canonical identity")
        object.__setattr__(self, "requirement_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "required_evidence_types": list(self.required_evidence_types),
            "acceptable_fidelities": list(self.acceptable_fidelities),
            "acceptable_evidence_grades": list(self.acceptable_evidence_grades),
            "acceptable_verification_strengths": list(self.acceptable_verification_strengths),
            "required_environment_id": self.required_environment_id,
            "required_environment_fingerprint": self.required_environment_fingerprint,
            "required_numerical_policy_id": self.required_numerical_policy_id,
            "required_numerical_policy_fingerprint": self.required_numerical_policy_fingerprint,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"requirement_id": self.requirement_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationRequirement":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("required_evidence_types", "acceptable_fidelities", "acceptable_evidence_grades", "acceptable_verification_strengths"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification requirement")
        return item


def verification_requirement_from_obligation(
    obligation: Mapping[str, Any],
    *,
    acceptable_fidelities: Sequence[str],
    acceptable_evidence_grades: Sequence[str],
    acceptable_verification_strengths: Sequence[str] = (),
    required_environment_id: str = "",
    required_environment_fingerprint: str = "",
    required_numerical_policy_id: str = "",
    required_numerical_policy_fingerprint: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> VerificationRequirement:
    row = _canonical_obligation(obligation)
    if not row["required_evidence_types"]:
        raise ValueError("verification requirement can only bind an existing obligation with required_evidence_types")
    return VerificationRequirement(
        obligation_id=row["obligation_id"],
        obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
        required_evidence_types=tuple(row["required_evidence_types"]),
        acceptable_fidelities=tuple(acceptable_fidelities),
        acceptable_evidence_grades=tuple(acceptable_evidence_grades),
        acceptable_verification_strengths=tuple(acceptable_verification_strengths),
        required_environment_id=required_environment_id,
        required_environment_fingerprint=required_environment_fingerprint,
        required_numerical_policy_id=required_numerical_policy_id,
        required_numerical_policy_fingerprint=required_numerical_policy_fingerprint,
        metadata=dict(metadata or {}),
    )


@dataclass(frozen=True)
class VerificationAssignment:
    obligation_id: str
    obligation_semantic_fingerprint: str
    verifier_profile_id: str
    verifier_profile_fingerprint: str
    evidence_type: str
    verification_strength: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    assignment_id: str = ""

    def __post_init__(self) -> None:
        obligation_id = _required("assignment obligation_id", self.obligation_id)
        obligation_fingerprint = _sha256("assignment obligation_semantic_fingerprint", self.obligation_semantic_fingerprint)
        profile_id = _required("assignment verifier_profile_id", self.verifier_profile_id)
        profile_fingerprint = _sha256("assignment verifier_profile_fingerprint", self.verifier_profile_fingerprint)
        evidence_type = _required("assignment evidence_type", self.evidence_type)
        strength = _optional(self.verification_strength).upper()
        if strength and strength not in VERIFICATION_STRENGTHS:
            raise ValueError(f"unsupported assignment verification strength: {strength}")
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "obligation_semantic_fingerprint", obligation_fingerprint)
        object.__setattr__(self, "verifier_profile_id", profile_id)
        object.__setattr__(self, "verifier_profile_fingerprint", profile_fingerprint)
        object.__setattr__(self, "evidence_type", evidence_type)
        object.__setattr__(self, "verification_strength", strength)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verification-assignment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assignment_id)
        if supplied and supplied != derived:
            raise ValueError("verification assignment_id does not match canonical identity")
        object.__setattr__(self, "assignment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "verifier_profile_id": self.verifier_profile_id,
            "verifier_profile_fingerprint": self.verifier_profile_fingerprint,
            "evidence_type": self.evidence_type,
            "verification_strength": self.verification_strength,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assignment_id": self.assignment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assignment_id": self.assignment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationAssignment":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification assignment")
        return item


def _assignment_errors(
    requirement: VerificationRequirement,
    profile: VerifierCapabilityProfile,
    assignment: VerificationAssignment,
) -> list[str]:
    errors: list[str] = []
    if assignment.obligation_id != requirement.obligation_id or assignment.obligation_semantic_fingerprint != requirement.obligation_semantic_fingerprint:
        errors.append("ASSIGNMENT_OBLIGATION_MISMATCH")
    if assignment.verifier_profile_id != profile.profile_id or assignment.verifier_profile_fingerprint != profile.fingerprint:
        errors.append("ASSIGNMENT_VERIFIER_PROFILE_MISMATCH")
    if assignment.evidence_type not in requirement.required_evidence_types:
        errors.append("ASSIGNMENT_EVIDENCE_TYPE_NOT_REQUIRED")
    if assignment.evidence_type not in profile.capability.evidence_types:
        errors.append("ASSIGNMENT_VERIFIER_DOES_NOT_PRODUCE_EVIDENCE_TYPE")
    if profile.fidelity not in requirement.acceptable_fidelities:
        errors.append("ASSIGNMENT_FIDELITY_UNSATISFIED")
    if profile.evidence_grade not in requirement.acceptable_evidence_grades:
        errors.append("ASSIGNMENT_EVIDENCE_GRADE_UNSATISFIED")
    env = profile.environment_reference
    if requirement.required_environment_id:
        if env.object_id != requirement.required_environment_id or env.object_fingerprint != requirement.required_environment_fingerprint:
            errors.append("ASSIGNMENT_ENVIRONMENT_MISMATCH")
    numerical = profile.numerical_policy_reference
    if requirement.required_numerical_policy_id:
        if numerical.object_id != requirement.required_numerical_policy_id or numerical.object_fingerprint != requirement.required_numerical_policy_fingerprint:
            errors.append("ASSIGNMENT_NUMERICAL_POLICY_MISMATCH")
    if requirement.acceptable_verification_strengths:
        if not assignment.verification_strength:
            errors.append("ASSIGNMENT_VERIFICATION_STRENGTH_REQUIRED")
        elif assignment.verification_strength not in requirement.acceptable_verification_strengths:
            errors.append("ASSIGNMENT_VERIFICATION_STRENGTH_UNSATISFIED")
        elif assignment.verification_strength not in profile.verification_strengths:
            errors.append("ASSIGNMENT_VERIFIER_DOES_NOT_DECLARE_STRENGTH")
    elif assignment.verification_strength and assignment.verification_strength not in profile.verification_strengths:
        errors.append("ASSIGNMENT_VERIFIER_DOES_NOT_DECLARE_STRENGTH")
    return errors


@dataclass(frozen=True)
class VerificationPlan:
    problem_revision_id: str
    problem_revision_fingerprint: str
    calculus_state_fingerprint: str
    requirements: tuple[VerificationRequirement | Mapping[str, Any], ...]
    verifier_profiles: tuple[VerifierCapabilityProfile | Mapping[str, Any], ...]
    assignments: tuple[VerificationAssignment | Mapping[str, Any], ...]
    producer_principal_id: str
    evidence_ids: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    plan_id: str = ""
    contract_id: str = VERIFICATION_PLAN_CONTRACT_ID
    contract_version: str = VERIFICATION_PLAN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != VERIFICATION_PLAN_CONTRACT_ID or self.contract_version != VERIFICATION_PLAN_CONTRACT_VERSION:
            raise ValueError("unsupported verification-plan contract")
        revision_id = _required("plan problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("plan problem_revision_fingerprint", self.problem_revision_fingerprint)
        state_fingerprint = _sha256("plan calculus_state_fingerprint", self.calculus_state_fingerprint)
        requirements = tuple(
            row if isinstance(row, VerificationRequirement) else VerificationRequirement.from_dict(row)
            for row in self.requirements
        )
        requirement_ids = [row.obligation_id for row in requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("verification plan requires at most one requirement per canonical obligation")
        requirements = tuple(sorted(requirements, key=lambda row: row.obligation_id))
        profiles = tuple(
            row if isinstance(row, VerifierCapabilityProfile) else VerifierCapabilityProfile.from_dict(row)
            for row in self.verifier_profiles
        )
        profile_ids = [row.profile_id for row in profiles]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("verification plan verifier profile IDs must be unique")
        profiles = tuple(sorted(profiles, key=lambda row: row.profile_id))
        assignments = tuple(
            row if isinstance(row, VerificationAssignment) else VerificationAssignment.from_dict(row)
            for row in self.assignments
        )
        assignment_ids = [row.assignment_id for row in assignments]
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("verification assignment IDs must be unique")
        by_requirement = {row.obligation_id: row for row in requirements}
        by_profile = {row.profile_id: row for row in profiles}
        for assignment in assignments:
            requirement = by_requirement.get(assignment.obligation_id)
            profile = by_profile.get(assignment.verifier_profile_id)
            if requirement is None:
                raise ValueError(f"verification assignment references unknown requirement obligation: {assignment.obligation_id}")
            if profile is None:
                raise ValueError(f"verification assignment references unknown verifier profile: {assignment.verifier_profile_id}")
            errors = _assignment_errors(requirement, profile, assignment)
            if errors:
                raise ValueError(f"verification assignment is incompatible with requirement/profile: {errors}")
        assignments = tuple(sorted(assignments, key=lambda row: row.assignment_id))
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "calculus_state_fingerprint", state_fingerprint)
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "verifier_profiles", profiles)
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "producer_principal_id", _required("plan producer_principal_id", self.producer_principal_id))
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="plan evidence_id", allow_empty=False))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verification-plan-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.plan_id)
        if supplied and supplied != derived:
            raise ValueError("verification plan_id does not match canonical identity")
        object.__setattr__(self, "plan_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "calculus_state_fingerprint": self.calculus_state_fingerprint,
            "requirements": [row.to_dict() for row in self.requirements],
            "verifier_profiles": [row.to_dict() for row in self.verifier_profiles],
            "assignments": [row.to_dict() for row in self.assignments],
            "producer_principal_id": self.producer_principal_id,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"plan_id": self.plan_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationPlan":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("requirements", "verifier_profiles", "assignments", "evidence_ids"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification plan")
        return item


def validate_verification_plan(calculus_state: Mapping[str, Any], plan: VerificationPlan | Mapping[str, Any]) -> dict[str, Any]:
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    state_fingerprint = content_hash(state)
    errors: list[str] = []
    if item.calculus_state_fingerprint != state_fingerprint:
        errors.append("PLAN_CALCULUS_STATE_FINGERPRINT_MISMATCH")
    canonical = _verification_obligations(state)
    expected_ids = set(canonical)
    plan_ids = {row.obligation_id for row in item.requirements}
    if plan_ids != expected_ids:
        missing = sorted(expected_ids - plan_ids)
        extra = sorted(plan_ids - expected_ids)
        if missing:
            errors.append(f"PLAN_OMITS_CANONICAL_VERIFICATION_OBLIGATIONS:{missing}")
        if extra:
            errors.append(f"PLAN_REFERENCES_NON_VERIFICATION_OBLIGATIONS:{extra}")
    for requirement in item.requirements:
        row = canonical.get(requirement.obligation_id)
        if row is None:
            continue
        canonical_fingerprint = obligation_semantic_fingerprint(row)
        if requirement.obligation_semantic_fingerprint != canonical_fingerprint:
            errors.append(f"REQUIREMENT_OBLIGATION_FINGERPRINT_MISMATCH:{requirement.obligation_id}")
        if tuple(requirement.required_evidence_types) != tuple(row["required_evidence_types"]):
            errors.append(f"REQUIREMENT_WEAKENS_OR_ALTERS_CANONICAL_EVIDENCE_TYPES:{requirement.obligation_id}")
    return {
        "valid": not errors,
        "errors": errors,
        "plan_id": item.plan_id,
        "plan_fingerprint": item.fingerprint,
        "calculus_state_fingerprint": state_fingerprint,
        "canonical_verification_obligation_ids": sorted(expected_ids),
        "assigned_obligation_ids": sorted({row.obligation_id for row in item.assignments}),
        "unassigned_obligation_ids": sorted(expected_ids - {row.obligation_id for row in item.assignments}),
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "capability_abi": "EXISTING_AASM_CAPABILITY_ABI_VERIFIER_ONLY",
        "execution_authority": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


@dataclass(frozen=True)
class VerificationEvidenceApplicability:
    evidence_id: str
    obligation_id: str
    obligation_semantic_fingerprint: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    evidence_type: str
    fidelity: str
    evidence_grade: str
    status: str
    environment_id: str = ""
    environment_fingerprint: str = ""
    numerical_policy_id: str = ""
    numerical_policy_fingerprint: str = ""
    verification_strength: str = ""
    verifier_profile_id: str = ""
    verifier_profile_fingerprint: str = ""
    assessment_evidence_ids: tuple[str, ...] = ()
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    applicability_id: str = ""

    def __post_init__(self) -> None:
        evidence_id = _required("applicability evidence_id", self.evidence_id)
        obligation_id = _required("applicability obligation_id", self.obligation_id)
        obligation_fingerprint = _sha256("applicability obligation_semantic_fingerprint", self.obligation_semantic_fingerprint)
        revision_id = _required("applicability problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("applicability problem_revision_fingerprint", self.problem_revision_fingerprint)
        evidence_type = _required("applicability evidence_type", self.evidence_type)
        fidelity = _required("applicability fidelity", self.fidelity).upper()
        if fidelity not in VERIFICATION_FIDELITIES:
            raise ValueError(f"unsupported verification evidence fidelity: {fidelity}")
        grade = _required("applicability evidence_grade", self.evidence_grade)
        status = _required("applicability status", self.status).upper()
        if status not in VERIFICATION_EVIDENCE_APPLICABILITY_STATUSES:
            raise ValueError(f"unsupported verification evidence applicability status: {status}")
        environment_id = _optional(self.environment_id)
        environment_fingerprint = _optional(self.environment_fingerprint).lower()
        if bool(environment_id) != bool(environment_fingerprint):
            raise ValueError("verification evidence environment id/fingerprint must be supplied together")
        if environment_fingerprint:
            environment_fingerprint = _sha256("applicability environment_fingerprint", environment_fingerprint)
        numerical_id = _optional(self.numerical_policy_id)
        numerical_fingerprint = _optional(self.numerical_policy_fingerprint).lower()
        if bool(numerical_id) != bool(numerical_fingerprint):
            raise ValueError("verification evidence numerical-policy id/fingerprint must be supplied together")
        if numerical_fingerprint:
            numerical_fingerprint = _sha256("applicability numerical_policy_fingerprint", numerical_fingerprint)
        strength = _optional(self.verification_strength).upper()
        if strength and strength not in VERIFICATION_STRENGTHS:
            raise ValueError(f"unsupported applicability verification strength: {strength}")
        profile_id = _optional(self.verifier_profile_id)
        profile_fingerprint = _optional(self.verifier_profile_fingerprint).lower()
        if bool(profile_id) != bool(profile_fingerprint):
            raise ValueError("verification evidence verifier profile id/fingerprint must be supplied together")
        if profile_fingerprint:
            profile_fingerprint = _sha256("applicability verifier_profile_fingerprint", profile_fingerprint)
        assessments = _uniq(self.assessment_evidence_ids, name="applicability assessment evidence_id")
        reason = _optional(self.reason)
        if status != "APPLICABLE" and not reason:
            raise ValueError("non-APPLICABLE verification evidence requires a reason")
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "obligation_semantic_fingerprint", obligation_fingerprint)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "evidence_type", evidence_type)
        object.__setattr__(self, "fidelity", fidelity)
        object.__setattr__(self, "evidence_grade", grade)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "environment_id", environment_id)
        object.__setattr__(self, "environment_fingerprint", environment_fingerprint)
        object.__setattr__(self, "numerical_policy_id", numerical_id)
        object.__setattr__(self, "numerical_policy_fingerprint", numerical_fingerprint)
        object.__setattr__(self, "verification_strength", strength)
        object.__setattr__(self, "verifier_profile_id", profile_id)
        object.__setattr__(self, "verifier_profile_fingerprint", profile_fingerprint)
        object.__setattr__(self, "assessment_evidence_ids", assessments)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verification-applicability-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.applicability_id)
        if supplied and supplied != derived:
            raise ValueError("verification evidence applicability_id does not match canonical identity")
        object.__setattr__(self, "applicability_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "evidence_type": self.evidence_type,
            "fidelity": self.fidelity,
            "evidence_grade": self.evidence_grade,
            "status": self.status,
            "environment_id": self.environment_id,
            "environment_fingerprint": self.environment_fingerprint,
            "numerical_policy_id": self.numerical_policy_id,
            "numerical_policy_fingerprint": self.numerical_policy_fingerprint,
            "verification_strength": self.verification_strength,
            "verifier_profile_id": self.verifier_profile_id,
            "verifier_profile_fingerprint": self.verifier_profile_fingerprint,
            "assessment_evidence_ids": list(self.assessment_evidence_ids),
            "reason": self.reason,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"applicability_id": self.applicability_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"applicability_id": self.applicability_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationEvidenceApplicability":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["assessment_evidence_ids"] = tuple(payload.get("assessment_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification evidence applicability")
        return item


@dataclass(frozen=True)
class VerificationDebtItem:
    obligation_id: str
    obligation_semantic_fingerprint: str
    obligation_status: str
    classification: str
    statement: str
    required_evidence_types: tuple[str, ...]
    applicable_evidence_ids: tuple[str, ...] = ()
    planned_verifier_profile_ids: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    item_id: str = ""

    def __post_init__(self) -> None:
        obligation_id = _required("debt obligation_id", self.obligation_id)
        obligation_fingerprint = _sha256("debt obligation_semantic_fingerprint", self.obligation_semantic_fingerprint)
        status = _required("debt obligation_status", self.obligation_status).upper()
        if status not in OBLIGATION_STATUSES:
            raise ValueError(f"unsupported existing obligation status: {status}")
        classification = _required("debt classification", self.classification).upper()
        if classification not in VERIFICATION_DEBT_CLASSIFICATIONS:
            raise ValueError(f"unsupported verification debt classification: {classification}")
        expected = "TERMINAL_UNVERIFIED" if status in TERMINAL_UNRESOLVED_OBLIGATION_STATUSES else "UNVERIFIED"
        if classification != expected:
            raise ValueError("verification debt classification must derive from canonical obligation status")
        evidence_types = _uniq(self.required_evidence_types, name="debt required evidence type", allow_empty=False)
        evidence_ids = _uniq(self.applicable_evidence_ids, name="applicable evidence_id")
        verifier_ids = _uniq(self.planned_verifier_profile_ids, name="planned verifier profile_id")
        reasons = _uniq(self.reasons, name="verification debt reason", allow_empty=False)
        unknown = sorted(set(reasons) - set(VERIFICATION_DEBT_REASONS))
        if unknown:
            raise ValueError(f"unsupported verification debt reasons: {unknown}")
        object.__setattr__(self, "obligation_id", obligation_id)
        object.__setattr__(self, "obligation_semantic_fingerprint", obligation_fingerprint)
        object.__setattr__(self, "obligation_status", status)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "statement", _required("debt statement", self.statement))
        object.__setattr__(self, "required_evidence_types", evidence_types)
        object.__setattr__(self, "applicable_evidence_ids", evidence_ids)
        object.__setattr__(self, "planned_verifier_profile_ids", verifier_ids)
        object.__setattr__(self, "reasons", reasons)
        derived = f"verification-debt-item-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.item_id)
        if supplied and supplied != derived:
            raise ValueError("verification debt item_id does not match canonical identity")
        object.__setattr__(self, "item_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            "obligation_status": self.obligation_status,
            "classification": self.classification,
            "statement": self.statement,
            "required_evidence_types": list(self.required_evidence_types),
            "applicable_evidence_ids": list(self.applicable_evidence_ids),
            "planned_verifier_profile_ids": list(self.planned_verifier_profile_ids),
            "reasons": list(self.reasons),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"item_id": self.item_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"item_id": self.item_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationDebtItem":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("required_evidence_types", "applicable_evidence_ids", "planned_verifier_profile_ids", "reasons"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification debt item")
        return item


@dataclass(frozen=True)
class VerificationDebtProjection:
    problem_revision_id: str
    problem_revision_fingerprint: str
    calculus_state_fingerprint: str
    verification_plan_id: str
    verification_plan_fingerprint: str
    evidence_state_fingerprint: str
    applicability_fingerprint: str
    items: tuple[VerificationDebtItem | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    projection_id: str = ""
    contract_id: str = VERIFICATION_DEBT_CONTRACT_ID
    contract_version: str = VERIFICATION_DEBT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != VERIFICATION_DEBT_CONTRACT_ID or self.contract_version != VERIFICATION_DEBT_CONTRACT_VERSION:
            raise ValueError("unsupported verification-debt contract")
        object.__setattr__(self, "problem_revision_id", _required("debt problem_revision_id", self.problem_revision_id))
        object.__setattr__(self, "problem_revision_fingerprint", _sha256("debt problem_revision_fingerprint", self.problem_revision_fingerprint))
        object.__setattr__(self, "calculus_state_fingerprint", _sha256("debt calculus_state_fingerprint", self.calculus_state_fingerprint))
        object.__setattr__(self, "verification_plan_id", _required("debt verification_plan_id", self.verification_plan_id))
        object.__setattr__(self, "verification_plan_fingerprint", _sha256("debt verification_plan_fingerprint", self.verification_plan_fingerprint))
        object.__setattr__(self, "evidence_state_fingerprint", _sha256("debt evidence_state_fingerprint", self.evidence_state_fingerprint))
        object.__setattr__(self, "applicability_fingerprint", _sha256("debt applicability_fingerprint", self.applicability_fingerprint))
        items = tuple(row if isinstance(row, VerificationDebtItem) else VerificationDebtItem.from_dict(row) for row in self.items)
        ids = [row.obligation_id for row in items]
        if len(ids) != len(set(ids)):
            raise ValueError("verification debt permits at most one item per canonical obligation")
        object.__setattr__(self, "items", tuple(sorted(items, key=lambda row: row.obligation_id)))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"verification-debt-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.projection_id)
        if supplied and supplied != derived:
            raise ValueError("verification debt projection_id does not match canonical identity")
        object.__setattr__(self, "projection_id", derived)

    @property
    def terminal_unverified_count(self) -> int:
        return sum(row.classification == "TERMINAL_UNVERIFIED" for row in self.items)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "calculus_state_fingerprint": self.calculus_state_fingerprint,
            "verification_plan_id": self.verification_plan_id,
            "verification_plan_fingerprint": self.verification_plan_fingerprint,
            "evidence_state_fingerprint": self.evidence_state_fingerprint,
            "applicability_fingerprint": self.applicability_fingerprint,
            "items": [row.to_dict() for row in self.items],
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"projection_id": self.projection_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            **self.identity_payload(),
            "total_debt_count": len(self.items),
            "terminal_unverified_count": self.terminal_unverified_count,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationDebtProjection":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload.pop("total_debt_count", None)
        payload.pop("terminal_unverified_count", None)
        payload["items"] = tuple(payload.get("items") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="verification debt projection")
        return item


def _evidence_rows(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def _evidence_fingerprint(records: Iterable[Mapping[str, Any]]) -> str:
    rows = [deepcopy(dict(row)) for row in records]
    rows.sort(key=lambda row: str(row.get("evidence_id") or ""))
    return semantic_fingerprint(rows)


def _applicability_fingerprint(rows: Sequence[VerificationEvidenceApplicability]) -> str:
    return semantic_fingerprint([row.to_dict() for row in sorted(rows, key=lambda row: row.applicability_id)])


def _binding_reasons(
    requirement: VerificationRequirement,
    binding: VerificationEvidenceApplicability,
) -> list[str]:
    reasons: list[str] = []
    if binding.evidence_type not in requirement.required_evidence_types:
        reasons.append("EVIDENCE_TYPE_UNSATISFIED")
    if binding.fidelity not in requirement.acceptable_fidelities:
        reasons.append("EVIDENCE_FIDELITY_UNSATISFIED")
    if binding.evidence_grade not in requirement.acceptable_evidence_grades:
        reasons.append("EVIDENCE_GRADE_UNSATISFIED")
    if requirement.required_environment_id:
        if binding.environment_id != requirement.required_environment_id or binding.environment_fingerprint != requirement.required_environment_fingerprint:
            reasons.append("ENVIRONMENT_MISMATCH")
    if requirement.required_numerical_policy_id:
        if binding.numerical_policy_id != requirement.required_numerical_policy_id or binding.numerical_policy_fingerprint != requirement.required_numerical_policy_fingerprint:
            reasons.append("NUMERICAL_POLICY_MISMATCH")
    if requirement.acceptable_verification_strengths:
        if binding.verification_strength not in requirement.acceptable_verification_strengths:
            reasons.append("VERIFICATION_STRENGTH_UNSATISFIED")
    return reasons


def project_verification_debt(
    calculus_state: Mapping[str, Any],
    evidence_records: Iterable[Mapping[str, Any]],
    plan: VerificationPlan | Mapping[str, Any],
    applicability: Sequence[VerificationEvidenceApplicability | Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> VerificationDebtProjection:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    validation = validate_verification_plan(state, item)
    if not validation["valid"]:
        raise ValueError(f"verification debt requires a valid exact plan: {validation['errors']}")
    evidence_list = [deepcopy(dict(row)) for row in evidence_records]
    evidence = _evidence_rows(evidence_list)
    bindings = tuple(
        row if isinstance(row, VerificationEvidenceApplicability) else VerificationEvidenceApplicability.from_dict(row)
        for row in applicability
    )
    canonical = _verification_obligations(state)
    requirements = {row.obligation_id: row for row in item.requirements}
    assignments: dict[str, list[VerificationAssignment]] = {}
    for assignment in item.assignments:
        assignments.setdefault(assignment.obligation_id, []).append(assignment)

    by_obligation: dict[str, list[VerificationEvidenceApplicability]] = {}
    seen_applicability_ids: set[str] = set()
    for binding in bindings:
        if binding.applicability_id in seen_applicability_ids:
            raise ValueError(f"duplicate verification evidence applicability identity: {binding.applicability_id}")
        seen_applicability_ids.add(binding.applicability_id)
        requirement = requirements.get(binding.obligation_id)
        if requirement is None:
            raise ValueError(f"verification evidence applicability references non-plan obligation: {binding.obligation_id}")
        if binding.obligation_semantic_fingerprint != requirement.obligation_semantic_fingerprint:
            raise ValueError(f"verification evidence applicability obligation fingerprint mismatch: {binding.obligation_id}")
        if binding.problem_revision_id != item.problem_revision_id or binding.problem_revision_fingerprint != item.problem_revision_fingerprint:
            raise ValueError(f"verification evidence applicability ProblemRevision mismatch: {binding.applicability_id}")
        if binding.evidence_id not in evidence:
            raise ValueError(f"verification evidence applicability references unknown Evidence: {binding.evidence_id}")
        missing_assessments = sorted(set(binding.assessment_evidence_ids) - set(evidence))
        if missing_assessments:
            raise ValueError(f"verification evidence applicability assessment Evidence missing: {missing_assessments}")
        if binding.verifier_profile_id:
            profiles = {row.profile_id: row for row in item.verifier_profiles}
            profile = profiles.get(binding.verifier_profile_id)
            if profile is None or profile.fingerprint != binding.verifier_profile_fingerprint:
                raise ValueError(f"verification evidence applicability verifier profile mismatch: {binding.applicability_id}")
        by_obligation.setdefault(binding.obligation_id, []).append(binding)

    debt: list[VerificationDebtItem] = []
    for obligation_id, obligation in sorted(canonical.items()):
        requirement = requirements[obligation_id]
        obligation_bindings = by_obligation.get(obligation_id, [])
        attached_ids = set(obligation.get("evidence_ids") or [])
        active_attached = {
            evidence_id
            for evidence_id in attached_ids
            if evidence_id in evidence and str(evidence[evidence_id].get("status", "active")) == "active"
        }
        stale_attached = {
            evidence_id
            for evidence_id in attached_ids
            if evidence_id in evidence and str(evidence[evidence_id].get("status", "active")) != "active"
        }
        reasons: set[str] = set()
        applicable_ids: set[str] = set()
        mismatch_reasons: set[str] = set()
        indeterminate = False
        assessed_attached: set[str] = set()

        for binding in obligation_bindings:
            if binding.evidence_id not in attached_ids:
                continue
            assessed_attached.add(binding.evidence_id)
            row = evidence[binding.evidence_id]
            if str(row.get("status", "active")) != "active":
                reasons.add("STALE_EVIDENCE")
                continue
            if binding.status == "INDETERMINATE":
                indeterminate = True
                continue
            if binding.status != "APPLICABLE":
                continue
            failures = _binding_reasons(requirement, binding)
            if failures:
                mismatch_reasons.update(failures)
                continue
            applicable_ids.add(binding.evidence_id)

        if obligation["status"] in TERMINAL_UNRESOLVED_OBLIGATION_STATUSES:
            reasons.add("TERMINAL_UNRESOLVED")
        if not applicable_ids:
            if not attached_ids:
                reasons.add("NO_ATTACHED_EVIDENCE")
            elif stale_attached:
                reasons.add("STALE_EVIDENCE")
            if active_attached - assessed_attached:
                reasons.add("EVIDENCE_APPLICABILITY_UNASSESSED")
            reasons.update(mismatch_reasons)
            if indeterminate:
                reasons.add("INDETERMINATE_APPLICABILITY")
            if not mismatch_reasons and not indeterminate and active_attached and active_attached <= assessed_attached:
                reasons.add("EVIDENCE_TYPE_UNSATISFIED")
        if not assignments.get(obligation_id) and not applicable_ids:
            reasons.add("NO_VERIFIER_ASSIGNMENT")

        if reasons:
            classification = (
                "TERMINAL_UNVERIFIED"
                if obligation["status"] in TERMINAL_UNRESOLVED_OBLIGATION_STATUSES
                else "UNVERIFIED"
            )
            planned_profiles = tuple(sorted({row.verifier_profile_id for row in assignments.get(obligation_id, [])}))
            debt.append(
                VerificationDebtItem(
                    obligation_id=obligation_id,
                    obligation_semantic_fingerprint=obligation_semantic_fingerprint(obligation),
                    obligation_status=obligation["status"],
                    classification=classification,
                    statement=str(obligation.get("statement") or ""),
                    required_evidence_types=tuple(obligation["required_evidence_types"]),
                    applicable_evidence_ids=tuple(sorted(applicable_ids)),
                    planned_verifier_profile_ids=planned_profiles,
                    reasons=tuple(sorted(reasons)),
                )
            )

    return VerificationDebtProjection(
        problem_revision_id=item.problem_revision_id,
        problem_revision_fingerprint=item.problem_revision_fingerprint,
        calculus_state_fingerprint=content_hash(state),
        verification_plan_id=item.plan_id,
        verification_plan_fingerprint=item.fingerprint,
        evidence_state_fingerprint=_evidence_fingerprint(evidence_list),
        applicability_fingerprint=_applicability_fingerprint(bindings),
        items=tuple(debt),
        metadata=dict(metadata or {}),
    )


def validate_verification_debt_projection(
    calculus_state: Mapping[str, Any],
    evidence_records: Iterable[Mapping[str, Any]],
    plan: VerificationPlan | Mapping[str, Any],
    applicability: Sequence[VerificationEvidenceApplicability | Mapping[str, Any]],
    projection: VerificationDebtProjection | Mapping[str, Any],
) -> dict[str, Any]:
    item = projection if isinstance(projection, VerificationDebtProjection) else VerificationDebtProjection.from_dict(projection)
    expected = project_verification_debt(
        calculus_state,
        evidence_records,
        plan,
        applicability,
        metadata=item.metadata,
    )
    if item != expected:
        raise ValueError("verification debt projection is stale or mismatched for canonical obligations/applicable Evidence")
    return {
        "valid": True,
        "projection_id": item.projection_id,
        "projection_fingerprint": item.fingerprint,
        "total_debt_count": len(item.items),
        "terminal_unverified_count": item.terminal_unverified_count,
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "evidence_store": "EXISTING_AASM_EVIDENCE_ONLY",
        "parallel_truth_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


def verification_planning_contract() -> dict[str, Any]:
    return {
        "plan_contract_id": VERIFICATION_PLAN_CONTRACT_ID,
        "plan_contract_version": VERIFICATION_PLAN_CONTRACT_VERSION,
        "debt_contract_id": VERIFICATION_DEBT_CONTRACT_ID,
        "debt_contract_version": VERIFICATION_DEBT_CONTRACT_VERSION,
        "stability": VERIFICATION_PLANNING_STABILITY,
        "obligation_source": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "obligation_requirement_set": "EXACT_UNSATISFIED_OBLIGATIONS_WITH_CANONICAL_REQUIRED_EVIDENCE_TYPES",
        "verifier_abi": "COMPOSES_EXISTING_AASM_CAPABILITY_ABI_VERIFIER",
        "fidelity": {"values": list(VERIFICATION_FIDELITIES), "ordering": "NONE"},
        "evidence_grade": "OPAQUE_NAMED_GRADE_EXACT_ACCEPTABILITY_NO_IMPLICIT_ORDERING",
        "verification_strengths": {"source": "EXISTING_AASM_FORMAL_VERIFICATION_STRENGTHS", "ordering": "NONE"},
        "soundness_completeness": "DECLARATIVE_CLAIMS_NOT_PROOF_AUTHORITY",
        "cost_resources": "EXACT_EXISTING_RESOURCE_DEMAND_REFERENCES_ONLY_NO_RESERVATION",
        "environment": "EXACT_EXISTING_ENVIRONMENT_REFERENCE",
        "numerical_policy": "EXACT_EXISTING_NUMERICAL_POLICY_REFERENCE",
        "cache_reuse": "PERFORMANCE_ONLY_UNLESS_SEPARATELY_CERTIFIED_FOR_SEMANTIC_REUSE",
        "plan_assignment": "PROPOSAL_ONLY",
        "verifier_execution": "NONE",
        "effect_dispatch": "NONE",
        "resource_reservation": "NONE",
        "fact_authority": "NONE",
        "obligation_mutation": "NONE",
        "problem_mutation": "NONE",
        "verification_debt": "DETERMINISTIC_PROJECTION_REQUIRED_OBLIGATIONS_VS_ACTIVE_APPLICABLE_EXISTING_EVIDENCE",
        "debt_scalar_score": "NONE",
        "parallel_obligation_graph": "NONE",
        "parallel_evidence_store": "NONE",
        "parallel_truth_plane": "NONE",
        "parallel_resource_plane": "NONE",
        "parallel_authority_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "VERIFICATION_PLAN_CONTRACT_ID",
    "VERIFICATION_PLAN_CONTRACT_VERSION",
    "VERIFICATION_DEBT_CONTRACT_ID",
    "VERIFICATION_DEBT_CONTRACT_VERSION",
    "VERIFICATION_PLANNING_STABILITY",
    "VERIFICATION_FIDELITIES",
    "VERIFICATION_PROPERTY_CLAIM_KINDS",
    "VERIFICATION_PROPERTY_CLAIM_STATUSES",
    "VERIFICATION_REFERENCE_KINDS",
    "VERIFICATION_CACHE_REUSE_ELIGIBILITY",
    "VERIFICATION_EVIDENCE_APPLICABILITY_STATUSES",
    "VERIFICATION_DEBT_CLASSIFICATIONS",
    "VERIFICATION_DEBT_REASONS",
    "VerificationBoundReference",
    "VerificationPropertyClaim",
    "VerifierCapabilityProfile",
    "VerificationRequirement",
    "verification_requirement_from_obligation",
    "VerificationAssignment",
    "VerificationPlan",
    "validate_verification_plan",
    "VerificationEvidenceApplicability",
    "VerificationDebtItem",
    "VerificationDebtProjection",
    "project_verification_debt",
    "validate_verification_debt_projection",
    "verification_planning_contract",
]
