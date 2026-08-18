from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .rule import EngineeringRule
from .semantic_projection import SemanticSubjectRef
from .semantic_result import semantic_fingerprint


RISK_ENVELOPE_CONTRACT_ID = "aasm.risk.envelope.v1"
RISK_ENVELOPE_CONTRACT_VERSION = "0.1.0"
EFFECT_IRREVERSIBILITY_CONTRACT_ID = "aasm.effect.irreversibility.v1"
EFFECT_IRREVERSIBILITY_CONTRACT_VERSION = "0.1.0"
RISK_ASSESSMENT_CONTRACT_ID = "aasm.risk.assessment.v1"
RISK_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
RISK_IRREVERSIBILITY_STABILITY = "FOUNDATION_EXPERIMENTAL"

HAZARD_SEVERITIES = ("MINOR", "MAJOR", "SEVERE", "CATASTROPHIC")
HAZARD_TREATMENTS = ("PROHIBITED", "MITIGATION_REQUIRED", "EXPLICIT_ACCEPTANCE_REQUIRED", "ADVISORY")
HAZARD_STATUSES = ("PRESENT", "ABSENT", "UNKNOWN")
IRREVERSIBILITY_CLASSES = ("REVERSIBLE", "CONDITIONALLY_REVERSIBLE", "COSTLY_TO_REVERSE", "IRREVERSIBLE", "UNKNOWN")
ASSURANCE_LEVELS = ("BASELINE", "ELEVATED", "STRONG", "MAXIMUM")
RISK_ASSESSMENT_STATUSES = (
    "ADMISSIBLE_FOR_PROPOSAL",
    "BLOCKED_HARD_HAZARD",
    "BLOCKED_INDETERMINATE_HAZARD",
    "REQUIRES_MITIGATION",
    "REQUIRES_EXPLICIT_ACCEPTANCE",
    "REQUIRES_ADDITIONAL_ASSURANCE",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ASSURANCE_RANK = {name: index for index, name in enumerate(ASSURANCE_LEVELS)}
_IRREVERSIBILITY_RANK = {name: index for index, name in enumerate(IRREVERSIBILITY_CLASSES[:-1])}


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"risk/irreversibility {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"risk/irreversibility {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str) -> tuple[str, ...]:
    return tuple(sorted({_required(name, value) for value in values}))


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
        raise TypeError("binary floating-point values are forbidden in risk/irreversibility portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"risk/irreversibility value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class HazardRef:
    hazard_id: str
    rule_revision_id: str
    rule_fingerprint: str
    severity: str
    treatment: str
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        hazard_id = _required("hazard_id", self.hazard_id)
        rule_revision_id = _required("rule_revision_id", self.rule_revision_id)
        rule_fingerprint = _sha256("rule_fingerprint", self.rule_fingerprint)
        severity = _required("hazard severity", self.severity).upper()
        treatment = _required("hazard treatment", self.treatment).upper()
        if severity not in HAZARD_SEVERITIES:
            raise ValueError(f"unsupported hazard severity: {severity}")
        if treatment not in HAZARD_TREATMENTS:
            raise ValueError(f"unsupported hazard treatment: {treatment}")
        object.__setattr__(self, "hazard_id", hazard_id)
        object.__setattr__(self, "rule_revision_id", rule_revision_id)
        object.__setattr__(self, "rule_fingerprint", rule_fingerprint)
        object.__setattr__(self, "severity", severity)
        object.__setattr__(self, "treatment", treatment)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="hazard evidence_id"))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "hazard_id": self.hazard_id,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "severity": self.severity,
            "treatment": self.treatment,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "HazardRef":
        payload = deepcopy(dict(value)); supplied = str(payload.pop("fingerprint", "")).strip()
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("hazard reference fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RiskEnvelope:
    envelope_name: str
    subject: SemanticSubjectRef | Mapping[str, Any]
    problem_revision_id: str
    problem_revision_fingerprint: str
    hazards: tuple[HazardRef | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    envelope_id: str = ""
    contract_id: str = RISK_ENVELOPE_CONTRACT_ID
    contract_version: str = RISK_ENVELOPE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != RISK_ENVELOPE_CONTRACT_ID or self.contract_version != RISK_ENVELOPE_CONTRACT_VERSION:
            raise ValueError("unsupported risk-envelope contract")
        name = _required("envelope_name", self.envelope_name)
        subject = self.subject if isinstance(self.subject, SemanticSubjectRef) else SemanticSubjectRef.from_dict(self.subject)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint)
        if subject.revision_bound and (subject.revision_id != revision_id or subject.revision_fingerprint != revision_fingerprint):
            raise ValueError("risk envelope subject revision must match exact problem revision binding")
        hazards = tuple(v if isinstance(v, HazardRef) else HazardRef.from_dict(v) for v in self.hazards)
        if not hazards:
            raise ValueError("risk envelope requires at least one hazard reference")
        ids = [v.hazard_id for v in hazards]
        if len(ids) != len(set(ids)):
            raise ValueError("risk envelope hazard IDs must be unique")
        hazards = tuple(sorted(hazards, key=lambda v: v.hazard_id))
        object.__setattr__(self, "envelope_name", name)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "hazards", hazards)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"risk-envelope-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.envelope_id)
        if supplied and supplied != derived:
            raise ValueError("risk envelope_id does not match canonical identity")
        object.__setattr__(self, "envelope_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_name": self.envelope_name,
            "subject": self.subject.identity_payload(),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "hazards": [v.identity_payload() for v in self.hazards],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"envelope_id": self.envelope_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"envelope_id": self.envelope_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RiskEnvelope":
        payload = deepcopy(dict(value)); supplied = str(payload.pop("fingerprint", "")).strip()
        payload["hazards"] = tuple(payload.get("hazards") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("risk envelope fingerprint mismatch")
        return item


@dataclass(frozen=True)
class HazardObservation:
    hazard_id: str
    status: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        hazard_id = _required("hazard observation id", self.hazard_id)
        status = _required("hazard observation status", self.status).upper()
        if status not in HAZARD_STATUSES:
            raise ValueError(f"unsupported hazard observation status: {status}")
        object.__setattr__(self, "hazard_id", hazard_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="hazard observation evidence_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {"hazard_id": self.hazard_id, "status": self.status, "evidence_ids": list(self.evidence_ids)}

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()


@dataclass(frozen=True)
class EffectIrreversibility:
    operation: str
    subject: SemanticSubjectRef | Mapping[str, Any]
    classification: str
    recovery_operations: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    profile_id: str = ""
    contract_id: str = EFFECT_IRREVERSIBILITY_CONTRACT_ID
    contract_version: str = EFFECT_IRREVERSIBILITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != EFFECT_IRREVERSIBILITY_CONTRACT_ID or self.contract_version != EFFECT_IRREVERSIBILITY_CONTRACT_VERSION:
            raise ValueError("unsupported effect-irreversibility contract")
        operation = _required("operation", self.operation)
        subject = self.subject if isinstance(self.subject, SemanticSubjectRef) else SemanticSubjectRef.from_dict(self.subject)
        classification = _required("irreversibility classification", self.classification).upper()
        if classification not in IRREVERSIBILITY_CLASSES:
            raise ValueError(f"unsupported irreversibility classification: {classification}")
        recovery = _uniq(self.recovery_operations, name="recovery operation")
        if classification == "IRREVERSIBLE" and recovery:
            raise ValueError("IRREVERSIBLE effect cannot claim recovery operations")
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "recovery_operations", recovery)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="irreversibility evidence_id"))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = f"effect-irreversibility-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.profile_id)
        if supplied and supplied != derived:
            raise ValueError("effect irreversibility profile_id does not match canonical identity")
        object.__setattr__(self, "profile_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "operation": self.operation,
            "subject": self.subject.identity_payload(),
            "classification": self.classification,
            "recovery_operations": list(self.recovery_operations),
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"profile_id": self.profile_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"profile_id": self.profile_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectIrreversibility":
        payload = deepcopy(dict(value)); supplied = str(payload.pop("fingerprint", "")).strip()
        payload["recovery_operations"] = tuple(payload.get("recovery_operations") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("effect irreversibility fingerprint mismatch")
        return item


@dataclass(frozen=True)
class IrreversibilityAssurancePolicy:
    required_levels: Mapping[str, str]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {str(k).strip().upper(): str(v).strip().upper() for k, v in self.required_levels.items()}
        if set(required) != set(IRREVERSIBILITY_CLASSES):
            raise ValueError("irreversibility assurance policy must define every classification exactly once")
        if any(v not in ASSURANCE_LEVELS for v in required.values()):
            raise ValueError("irreversibility assurance policy contains unsupported assurance level")
        ordered = IRREVERSIBILITY_CLASSES[:-1]
        ranks = [_ASSURANCE_RANK[required[name]] for name in ordered]
        if ranks != sorted(ranks):
            raise ValueError("irreversibility assurance requirements must be monotonic with irreversibility")
        if required["UNKNOWN"] != "MAXIMUM":
            raise ValueError("UNKNOWN irreversibility must require MAXIMUM assurance")
        object.__setattr__(self, "required_levels", dict(sorted(required.items())))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def required_level(self, classification: str) -> str:
        return self.required_levels[str(classification).strip().upper()]

    def identity_payload(self) -> dict[str, Any]:
        return {"required_levels": dict(self.required_levels), "metadata": _jsonable(self.metadata)}

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class RiskAssessment:
    envelope_id: str
    envelope_fingerprint: str
    irreversibility_profile_id: str
    irreversibility_fingerprint: str
    status: str
    required_assurance_level: str
    available_assurance_level: str
    blocking_hazard_ids: tuple[str, ...] = ()
    mitigation_hazard_ids: tuple[str, ...] = ()
    acceptance_hazard_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    effect_authority_granted: bool = False
    rule_waiver_performed: bool = False
    objective_override_performed: bool = False
    resource_override_performed: bool = False
    artifact_acceptance_granted: bool = False
    assessment_id: str = ""
    contract_id: str = RISK_ASSESSMENT_CONTRACT_ID
    contract_version: str = RISK_ASSESSMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("envelope_id", "irreversibility_profile_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in ("envelope_fingerprint", "irreversibility_fingerprint"):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        if self.contract_id != RISK_ASSESSMENT_CONTRACT_ID or self.contract_version != RISK_ASSESSMENT_CONTRACT_VERSION:
            raise ValueError("unsupported risk-assessment contract")
        status = _required("risk assessment status", self.status).upper()
        required_level = _required("required assurance level", self.required_assurance_level).upper()
        available_level = _required("available assurance level", self.available_assurance_level).upper()
        if status not in RISK_ASSESSMENT_STATUSES:
            raise ValueError(f"unsupported risk assessment status: {status}")
        if required_level not in ASSURANCE_LEVELS or available_level not in ASSURANCE_LEVELS:
            raise ValueError("unsupported risk assessment assurance level")
        if any((self.effect_authority_granted, self.rule_waiver_performed, self.objective_override_performed, self.resource_override_performed, self.artifact_acceptance_granted)):
            raise ValueError("risk assessment cannot claim authority, waiver, objective/resource override, or artifact acceptance")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "required_assurance_level", required_level)
        object.__setattr__(self, "available_assurance_level", available_level)
        for name in ("blocking_hazard_ids", "mitigation_hazard_ids", "acceptance_hazard_ids", "diagnostics"):
            object.__setattr__(self, name, _uniq(getattr(self, name), name=name))
        derived = f"risk-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError("risk assessment_id does not match canonical identity")
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_id": self.envelope_id,
            "envelope_fingerprint": self.envelope_fingerprint,
            "irreversibility_profile_id": self.irreversibility_profile_id,
            "irreversibility_fingerprint": self.irreversibility_fingerprint,
            "status": self.status,
            "required_assurance_level": self.required_assurance_level,
            "available_assurance_level": self.available_assurance_level,
            "blocking_hazard_ids": list(self.blocking_hazard_ids),
            "mitigation_hazard_ids": list(self.mitigation_hazard_ids),
            "acceptance_hazard_ids": list(self.acceptance_hazard_ids),
            "diagnostics": list(self.diagnostics),
            "effect_authority_granted": False,
            "rule_waiver_performed": False,
            "objective_override_performed": False,
            "resource_override_performed": False,
            "artifact_acceptance_granted": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assessment_id": self.assessment_id, **self.identity_payload(), "fingerprint": self.fingerprint}



def evaluate_risk(
    envelope: RiskEnvelope,
    rules: Sequence[EngineeringRule],
    observations: Sequence[HazardObservation],
    irreversibility: EffectIrreversibility,
    assurance_policy: IrreversibilityAssurancePolicy,
    *,
    available_assurance_level: str,
) -> RiskAssessment:
    if not isinstance(envelope, RiskEnvelope) or not isinstance(irreversibility, EffectIrreversibility) or not isinstance(assurance_policy, IrreversibilityAssurancePolicy):
        raise TypeError("evaluate_risk requires typed risk envelope, irreversibility profile, and assurance policy")
    if irreversibility.subject != envelope.subject:
        raise ValueError("risk envelope and irreversibility profile must bind the exact same semantic subject")
    available = _required("available_assurance_level", available_assurance_level).upper()
    if available not in ASSURANCE_LEVELS:
        raise ValueError("unsupported available assurance level")

    rules_by_id = {rule.rule_revision_id: rule for rule in rules}
    if len(rules_by_id) != len(tuple(rules)):
        raise ValueError("risk evaluation rules must have unique rule_revision_id")
    observations_by_id = {row.hazard_id: row for row in observations}
    if len(observations_by_id) != len(tuple(observations)):
        raise ValueError("risk evaluation observations must have unique hazard_id")
    if set(observations_by_id) != {hazard.hazard_id for hazard in envelope.hazards}:
        raise ValueError("risk evaluation requires exactly one observation for every envelope hazard")

    blocking: list[str] = []
    mitigation: list[str] = []
    acceptance: list[str] = []
    diagnostics: list[str] = []
    unknown_hard: list[str] = []

    for hazard in envelope.hazards:
        rule = rules_by_id.get(hazard.rule_revision_id)
        if rule is None or rule.fingerprint != hazard.rule_fingerprint:
            raise ValueError(f"risk hazard {hazard.hazard_id} does not bind an exact supplied EngineeringRule")
        if rule.problem_revision_id and rule.problem_revision_id != envelope.problem_revision_id:
            raise ValueError(f"risk hazard {hazard.hazard_id} EngineeringRule problem revision mismatch")
        if hazard.treatment == "PROHIBITED" and rule.strength != "HARD_FLOOR":
            raise ValueError("PROHIBITED risk hazards must be backed by an exact HARD_FLOOR EngineeringRule")
        observation = observations_by_id[hazard.hazard_id]
        if observation.status == "UNKNOWN":
            if hazard.treatment == "PROHIBITED":
                unknown_hard.append(hazard.hazard_id)
            else:
                diagnostics.append(f"UNKNOWN_HAZARD:{hazard.hazard_id}")
            continue
        if observation.status == "ABSENT":
            continue
        if hazard.treatment == "PROHIBITED":
            blocking.append(hazard.hazard_id)
        elif hazard.treatment == "MITIGATION_REQUIRED":
            mitigation.append(hazard.hazard_id)
        elif hazard.treatment == "EXPLICIT_ACCEPTANCE_REQUIRED":
            acceptance.append(hazard.hazard_id)
        else:
            diagnostics.append(f"ADVISORY_HAZARD_PRESENT:{hazard.hazard_id}")

    required = assurance_policy.required_level(irreversibility.classification)
    if blocking:
        status = "BLOCKED_HARD_HAZARD"
    elif unknown_hard:
        status = "BLOCKED_INDETERMINATE_HAZARD"
        blocking.extend(unknown_hard)
    elif mitigation:
        status = "REQUIRES_MITIGATION"
    elif acceptance:
        status = "REQUIRES_EXPLICIT_ACCEPTANCE"
    elif _ASSURANCE_RANK[available] < _ASSURANCE_RANK[required]:
        status = "REQUIRES_ADDITIONAL_ASSURANCE"
    else:
        status = "ADMISSIBLE_FOR_PROPOSAL"

    return RiskAssessment(
        envelope.envelope_id,
        envelope.fingerprint,
        irreversibility.profile_id,
        irreversibility.fingerprint,
        status,
        required,
        available,
        tuple(blocking),
        tuple(mitigation),
        tuple(acceptance),
        tuple(diagnostics),
    )


def risk_irreversibility_contract() -> dict[str, Any]:
    return {
        "risk_contract_id": RISK_ENVELOPE_CONTRACT_ID,
        "risk_contract_version": RISK_ENVELOPE_CONTRACT_VERSION,
        "irreversibility_contract_id": EFFECT_IRREVERSIBILITY_CONTRACT_ID,
        "irreversibility_contract_version": EFFECT_IRREVERSIBILITY_CONTRACT_VERSION,
        "assessment_contract_id": RISK_ASSESSMENT_CONTRACT_ID,
        "assessment_contract_version": RISK_ASSESSMENT_CONTRACT_VERSION,
        "stability": RISK_IRREVERSIBILITY_STABILITY,
        "hazard_severities": list(HAZARD_SEVERITIES),
        "hazard_treatments": list(HAZARD_TREATMENTS),
        "hazard_statuses": list(HAZARD_STATUSES),
        "irreversibility_classes": list(IRREVERSIBILITY_CLASSES),
        "assurance_levels": list(ASSURANCE_LEVELS),
        "hard_hazard_legality": "EXACT_EXISTING_AASM_RULE_V1_HARD_FLOOR_REFERENCE_ONLY_NO_SECOND_HARD_FLOOR_SYSTEM",
        "risk_cost_relation": "RISK_IS_NOT_RESOURCE_OR_MONETARY_COST_AND_HAS_NO_SCALAR_COST_COLLAPSE",
        "optimization_relation": "OBJECTIVE_IMPROVEMENT_CANNOT_OVERRIDE_PRESENT_OR_UNKNOWN_HARD_HAZARD",
        "resource_relation": "RESOURCE_SCARCITY_CANNOT_RELAX_HARD_HAZARD_OR_ASSURANCE_REQUIREMENT",
        "hazard_observation_authority": "EXPLICIT_POLICY_INPUT_WITH_EVIDENCE_REFERENCES_NOT_FACT_AUTHORITY",
        "explicit_acceptance": "REQUIREMENT_ONLY_NO_WAIVER_OR_AUTHORIZATION_PERFORMED_BY_FOUNDATION",
        "irreversibility_assurance": "EXPLICIT_MONOTONIC_PROFILE_POLICY_UNKNOWN_REQUIRES_MAXIMUM",
        "irreversibility_is_effect_authority": False,
        "risk_assessment_is_effect_authority": False,
        "risk_assessment_is_rule_waiver": False,
        "risk_assessment_is_artifact_acceptance": False,
        "risk_assessment_proves_empirical_safety": False,
        "parallel_risk_registry": "NONE",
        "parallel_hazard_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_resource_plane": "NONE",
        "parallel_objective_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "RISK_ENVELOPE_CONTRACT_ID", "RISK_ENVELOPE_CONTRACT_VERSION",
    "EFFECT_IRREVERSIBILITY_CONTRACT_ID", "EFFECT_IRREVERSIBILITY_CONTRACT_VERSION",
    "RISK_ASSESSMENT_CONTRACT_ID", "RISK_ASSESSMENT_CONTRACT_VERSION", "RISK_IRREVERSIBILITY_STABILITY",
    "HAZARD_SEVERITIES", "HAZARD_TREATMENTS", "HAZARD_STATUSES", "IRREVERSIBILITY_CLASSES",
    "ASSURANCE_LEVELS", "RISK_ASSESSMENT_STATUSES", "HazardRef", "RiskEnvelope", "HazardObservation",
    "EffectIrreversibility", "IrreversibilityAssurancePolicy", "RiskAssessment", "evaluate_risk",
    "risk_irreversibility_contract",
]
