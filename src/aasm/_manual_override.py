from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .calculus import OBLIGATION_STATUSES, normalize_calculus_state
from .obligation_phase import obligation_semantic_fingerprint
from .risk_irreversibility import RiskAssessment
from .rule import EngineeringRule, RuleSourceAuthorityRef
from .semantic_result import semantic_fingerprint


MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"
MANUAL_OVERRIDE_CONTRACT_VERSION = "0.1.0"
MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"
MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
MANUAL_OVERRIDE_STABILITY = "FOUNDATION_EXPERIMENTAL"
MANUAL_OVERRIDE_ASSESSMENT_STATUSES = (
    "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW",
    "BLOCKED_HARD_FLOOR",
    "BLOCKED_RULE_POLICY",
    "BLOCKED_AUTHORITY_REFERENCE",
    "BLOCKED_ACCEPTED_RISK",
    "BLOCKED_RESULTING_OBLIGATIONS",
    "OUTSIDE_VALIDITY_WINDOW",
)
SATISFIED_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
TERMINAL_OBLIGATION_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"manual-override {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(
            f"manual-override {name} must be a lowercase 64-hex SHA-256 digest"
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
            "binary floating-point values are forbidden in manual-override portable identity"
        )
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"manual-override value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class OverrideValidityWindow:
    clock_id: str
    not_before_sequence: int
    not_after_sequence: int

    def __post_init__(self) -> None:
        clock_id = _required("validity clock_id", self.clock_id)
        for name in ("not_before_sequence", "not_after_sequence"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"manual override {name} must be an exact non-negative integer"
                )
        if self.not_after_sequence <= self.not_before_sequence:
            raise ValueError(
                "manual override not_after_sequence must be greater than not_before_sequence"
            )
        object.__setattr__(self, "clock_id", clock_id)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "clock_id": self.clock_id,
            "not_before_sequence": self.not_before_sequence,
            "not_after_sequence": self.not_after_sequence,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OverrideValidityWindow":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("manual override validity-window fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ResultingObligationRef:
    obligation_id: str
    obligation_semantic_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "obligation_id",
            _required("resulting obligation_id", self.obligation_id),
        )
        object.__setattr__(
            self,
            "obligation_semantic_fingerprint",
            _sha256(
                "resulting obligation_semantic_fingerprint",
                self.obligation_semantic_fingerprint,
            ),
        )

    def identity_payload(self) -> dict[str, str]:
        return {
            "obligation_id": self.obligation_id,
            "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, str]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResultingObligationRef":
        payload = dict(value)
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("resulting obligation reference fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ManualOverride:
    principal_id: str
    rule_revision_id: str
    rule_fingerprint: str
    rule_id: str
    reason: str
    workspace_id: str
    scope_id: str
    scope_selector_fingerprint: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    validity: OverrideValidityWindow | Mapping[str, Any]
    accepted_risk_assessment_id: str
    accepted_risk_assessment_fingerprint: str
    accepted_hazard_ids: tuple[str, ...]
    authority: RuleSourceAuthorityRef | Mapping[str, Any]
    authority_evidence_ids: tuple[str, ...]
    resulting_obligations: tuple[ResultingObligationRef | Mapping[str, Any], ...]
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    override_id: str = ""
    contract_id: str = MANUAL_OVERRIDE_CONTRACT_ID
    contract_version: str = MANUAL_OVERRIDE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != MANUAL_OVERRIDE_CONTRACT_ID
            or self.contract_version != MANUAL_OVERRIDE_CONTRACT_VERSION
        ):
            raise ValueError("unsupported manual-override contract")
        principal_id = _required("principal_id", self.principal_id)
        rule_revision_id = _required("rule_revision_id", self.rule_revision_id)
        rule_fingerprint = _sha256("rule_fingerprint", self.rule_fingerprint)
        rule_id = _required("rule_id", self.rule_id)
        reason = _required("reason", self.reason)
        workspace_id = _required("workspace_id", self.workspace_id)
        scope_id = _optional(self.scope_id)
        selector_fingerprint = _sha256(
            "scope_selector_fingerprint",
            self.scope_selector_fingerprint,
        )
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256(
            "problem_revision_fingerprint",
            self.problem_revision_fingerprint,
        )
        validity = (
            self.validity
            if isinstance(self.validity, OverrideValidityWindow)
            else OverrideValidityWindow.from_dict(self.validity)
        )
        risk_id = _required(
            "accepted_risk_assessment_id",
            self.accepted_risk_assessment_id,
        )
        risk_fingerprint = _sha256(
            "accepted_risk_assessment_fingerprint",
            self.accepted_risk_assessment_fingerprint,
        )
        accepted_hazards = _uniq(
            self.accepted_hazard_ids,
            name="accepted hazard_id",
        )
        if not accepted_hazards:
            raise ValueError(
                "manual override requires at least one explicitly accepted hazard"
            )
        authority = (
            self.authority
            if isinstance(self.authority, RuleSourceAuthorityRef)
            else RuleSourceAuthorityRef.from_dict(self.authority)
        )
        if authority.principal_id != principal_id:
            raise ValueError(
                "manual override principal_id must match its exact scoped-authority reference"
            )
        authority_evidence_ids = _uniq(
            self.authority_evidence_ids,
            name="authority evidence_id",
        )
        if not authority_evidence_ids:
            raise ValueError("manual override requires explicit authority evidence IDs")
        resulting = tuple(
            value
            if isinstance(value, ResultingObligationRef)
            else ResultingObligationRef.from_dict(value)
            for value in self.resulting_obligations
        )
        if not resulting:
            raise ValueError(
                "manual override requires at least one resulting existing obligation reference"
            )
        ids = [value.obligation_id for value in resulting]
        if len(ids) != len(set(ids)):
            raise ValueError(
                "manual override resulting obligation references must be unique"
            )
        resulting = tuple(sorted(resulting, key=lambda value: value.obligation_id))
        object.__setattr__(self, "principal_id", principal_id)
        object.__setattr__(self, "rule_revision_id", rule_revision_id)
        object.__setattr__(self, "rule_fingerprint", rule_fingerprint)
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "workspace_id", workspace_id)
        object.__setattr__(self, "scope_id", scope_id)
        object.__setattr__(
            self,
            "scope_selector_fingerprint",
            selector_fingerprint,
        )
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(
            self,
            "problem_revision_fingerprint",
            revision_fingerprint,
        )
        object.__setattr__(self, "validity", validity)
        object.__setattr__(self, "accepted_risk_assessment_id", risk_id)
        object.__setattr__(
            self,
            "accepted_risk_assessment_fingerprint",
            risk_fingerprint,
        )
        object.__setattr__(self, "accepted_hazard_ids", accepted_hazards)
        object.__setattr__(self, "authority", authority)
        object.__setattr__(
            self,
            "authority_evidence_ids",
            authority_evidence_ids,
        )
        object.__setattr__(self, "resulting_obligations", resulting)
        object.__setattr__(
            self,
            "evidence_ids",
            _uniq(self.evidence_ids, name="override evidence_id"),
        )
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = (
            f"manual-override-{semantic_fingerprint(self.identity_payload())[:24]}"
        )
        supplied = _optional(self.override_id)
        if supplied and supplied != derived:
            raise ValueError("manual override_id does not match canonical identity")
        object.__setattr__(self, "override_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "principal_id": self.principal_id,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "scope_selector_fingerprint": self.scope_selector_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "validity": self.validity.identity_payload(),
            "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
            "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
            "accepted_hazard_ids": list(self.accepted_hazard_ids),
            "authority": self.authority.identity_payload(),
            "authority_evidence_ids": list(self.authority_evidence_ids),
            "resulting_obligations": [
                value.identity_payload() for value in self.resulting_obligations
            ],
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            {"override_id": self.override_id, **self.identity_payload()}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "override_id": self.override_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "principal_id": self.principal_id,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "rule_id": self.rule_id,
            "reason": self.reason,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "scope_selector_fingerprint": self.scope_selector_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "validity": self.validity.to_dict(),
            "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
            "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
            "accepted_hazard_ids": list(self.accepted_hazard_ids),
            "authority": self.authority.identity_payload(),
            "authority_evidence_ids": list(self.authority_evidence_ids),
            "resulting_obligations": [
                value.to_dict() for value in self.resulting_obligations
            ],
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ManualOverride":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["accepted_hazard_ids"] = tuple(payload.get("accepted_hazard_ids") or ())
        payload["authority_evidence_ids"] = tuple(
            payload.get("authority_evidence_ids") or ()
        )
        payload["resulting_obligations"] = tuple(
            payload.get("resulting_obligations") or ()
        )
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("manual override fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ManualOverrideAssessment:
    override_id: str
    override_fingerprint: str
    rule_revision_id: str
    rule_fingerprint: str
    accepted_risk_assessment_id: str
    accepted_risk_assessment_fingerprint: str
    status: str
    diagnostics: tuple[str, ...] = ()
    waiver_performed: bool = False
    rule_mutated: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    obligation_mutated: bool = False
    history_deleted: bool = False
    current_override_activated: bool = False
    assessment_id: str = ""
    contract_id: str = MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID
    contract_version: str = MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID
            or self.contract_version != MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION
        ):
            raise ValueError("unsupported manual-override assessment contract")
        for name in (
            "override_id",
            "rule_revision_id",
            "accepted_risk_assessment_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in (
            "override_fingerprint",
            "rule_fingerprint",
            "accepted_risk_assessment_fingerprint",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        status = _required("assessment status", self.status).upper()
        if status not in MANUAL_OVERRIDE_ASSESSMENT_STATUSES:
            raise ValueError(f"unsupported manual override assessment status: {status}")
        for name in (
            "waiver_performed",
            "rule_mutated",
            "authority_granted",
            "effect_authority_granted",
            "obligation_mutated",
            "history_deleted",
            "current_override_activated",
        ):
            if bool(getattr(self, name)):
                raise ValueError(f"manual override assessment cannot set {name}=True")
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "diagnostics",
            _uniq(self.diagnostics, name="assessment diagnostic"),
        )
        derived = f"manual-override-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError(
                "manual override assessment_id does not match canonical identity"
            )
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "override_id": self.override_id,
            "override_fingerprint": self.override_fingerprint,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
            "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
            "status": self.status,
            "diagnostics": list(self.diagnostics),
            "waiver_performed": False,
            "rule_mutated": False,
            "authority_granted": False,
            "effect_authority_granted": False,
            "obligation_mutated": False,
            "history_deleted": False,
            "current_override_activated": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(
            {"assessment_id": self.assessment_id, **self.identity_payload()}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ManualOverrideAssessment":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("manual override assessment fingerprint mismatch")
        return item


def bind_manual_override(
    rule: EngineeringRule,
    risk_assessment: RiskAssessment,
    obligations: Sequence[Mapping[str, Any]],
    *,
    principal_id: str,
    authority: RuleSourceAuthorityRef,
    reason: str,
    validity: OverrideValidityWindow,
    problem_revision_id: str,
    problem_revision_fingerprint: str,
    authority_evidence_ids: Sequence[str],
    accepted_hazard_ids: Sequence[str] | None = None,
    evidence_ids: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> ManualOverride:
    if not isinstance(rule, EngineeringRule):
        raise TypeError("bind_manual_override requires an exact EngineeringRule")
    if not isinstance(risk_assessment, RiskAssessment):
        raise TypeError("bind_manual_override requires an exact RiskAssessment")
    if not isinstance(authority, RuleSourceAuthorityRef):
        raise TypeError(
            "bind_manual_override requires an exact existing RuleSourceAuthorityRef"
        )
    if not isinstance(validity, OverrideValidityWindow):
        raise TypeError("bind_manual_override requires an explicit validity window")
    refs = tuple(
        ResultingObligationRef(
            obligation_id=str(row.get("obligation_id") or ""),
            obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
        )
        for row in obligations
    )
    return ManualOverride(
        principal_id=principal_id,
        rule_revision_id=rule.rule_revision_id,
        rule_fingerprint=rule.fingerprint,
        rule_id=rule.rule_id,
        reason=reason,
        workspace_id=rule.scope_selector.workspace_id,
        scope_id=rule.scope_selector.scope_id,
        scope_selector_fingerprint=rule.scope_selector.fingerprint,
        problem_revision_id=problem_revision_id,
        problem_revision_fingerprint=problem_revision_fingerprint,
        validity=validity,
        accepted_risk_assessment_id=risk_assessment.assessment_id,
        accepted_risk_assessment_fingerprint=risk_assessment.fingerprint,
        accepted_hazard_ids=tuple(
            risk_assessment.acceptance_hazard_ids
            if accepted_hazard_ids is None
            else accepted_hazard_ids
        ),
        authority=authority,
        authority_evidence_ids=tuple(authority_evidence_ids),
        resulting_obligations=refs,
        evidence_ids=tuple(evidence_ids),
        metadata=dict(metadata or {}),
    )


def evaluate_manual_override(
    override: ManualOverride | Mapping[str, Any],
    rules: Sequence[EngineeringRule],
    risk_assessments: Sequence[RiskAssessment],
    calculus_state: Mapping[str, Any],
    *,
    clock_id: str,
    sequence: int,
) -> ManualOverrideAssessment:
    item = (
        override
        if isinstance(override, ManualOverride)
        else ManualOverride.from_dict(override)
    )
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ValueError("manual override evaluation sequence must be non-negative")
    current_clock = _required("evaluation clock_id", clock_id)
    rule_rows = tuple(rules)
    if any(not isinstance(rule, EngineeringRule) for rule in rule_rows):
        raise TypeError(
            "manual override evaluation requires exact EngineeringRule objects"
        )
    rules_by_id = {rule.rule_revision_id: rule for rule in rule_rows}
    if len(rules_by_id) != len(rule_rows):
        raise ValueError("manual override evaluation rules must have unique identities")
    rule = rules_by_id.get(item.rule_revision_id)
    if rule is None or rule.fingerprint != item.rule_fingerprint:
        raise ValueError(
            "manual override does not bind an exact supplied EngineeringRule"
        )
    if rule.rule_id != item.rule_id:
        raise ValueError("manual override rule_id mismatch")
    if (
        rule.scope_selector.workspace_id != item.workspace_id
        or rule.scope_selector.scope_id != item.scope_id
        or rule.scope_selector.fingerprint != item.scope_selector_fingerprint
    ):
        raise ValueError(
            "manual override scope does not match the exact Rule scope selector"
        )
    if rule.problem_revision_id and (
        rule.problem_revision_id != item.problem_revision_id
        or rule.problem_revision_fingerprint != item.problem_revision_fingerprint
    ):
        raise ValueError("manual override EngineeringRule ProblemRevision mismatch")

    risk_rows = tuple(risk_assessments)
    if any(not isinstance(value, RiskAssessment) for value in risk_rows):
        raise TypeError(
            "manual override evaluation requires exact RiskAssessment objects"
        )
    risks_by_id = {value.assessment_id: value for value in risk_rows}
    if len(risks_by_id) != len(risk_rows):
        raise ValueError("manual override risk assessments must have unique identities")
    risk = risks_by_id.get(item.accepted_risk_assessment_id)
    if risk is None or risk.fingerprint != item.accepted_risk_assessment_fingerprint:
        raise ValueError(
            "manual override does not bind an exact supplied RiskAssessment"
        )

    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    obligations = dict(state.get("obligations") or {})
    obligation_statuses: list[str] = []
    for reference in item.resulting_obligations:
        row = obligations.get(reference.obligation_id)
        if row is None:
            raise ValueError(
                "manual override resulting obligation reference is absent from the existing calculus store"
            )
        if (
            obligation_semantic_fingerprint(row)
            != reference.obligation_semantic_fingerprint
        ):
            raise ValueError(
                "manual override resulting obligation reference is stale or mismatched"
            )
        status = str(row.get("status") or "AVAILABLE").upper()
        if status not in OBLIGATION_STATUSES:
            raise ValueError(
                "manual override encountered unsupported obligation status"
            )
        obligation_statuses.append(status)

    diagnostics: list[str] = []
    if rule.strength == "HARD_FLOOR":
        status = "BLOCKED_HARD_FLOOR"
        diagnostics.append("HARD_FLOOR_RULE_CANNOT_BE_WAIVED_OR_OVERRIDDEN")
    elif rule.control_policy.waiver_mode != "EXPLICIT_AUTHORIZED":
        status = "BLOCKED_RULE_POLICY"
        diagnostics.append("RULE_WAIVER_MODE_IS_NOT_EXPLICIT_AUTHORIZED")
    elif item.authority.capability != rule.control_policy.required_capability:
        status = "BLOCKED_AUTHORITY_REFERENCE"
        diagnostics.append("AUTHORITY_CAPABILITY_DOES_NOT_MATCH_RULE_POLICY")
    elif (
        risk.status != "REQUIRES_EXPLICIT_ACCEPTANCE"
        or tuple(item.accepted_hazard_ids) != tuple(risk.acceptance_hazard_ids)
        or bool(risk.blocking_hazard_ids)
        or bool(risk.mitigation_hazard_ids)
    ):
        status = "BLOCKED_ACCEPTED_RISK"
        diagnostics.append(
            "RISK_ASSESSMENT_IS_NOT_EXACTLY_ACCEPTABLE_BY_MANUAL_OVERRIDE"
        )
    elif any(
        value in SATISFIED_OBLIGATION_STATUSES + TERMINAL_OBLIGATION_STATUSES
        for value in obligation_statuses
    ):
        status = "BLOCKED_RESULTING_OBLIGATIONS"
        diagnostics.append(
            "RESULTING_OBLIGATIONS_MUST_BE_EXISTING_OUTSTANDING_NONTERMINAL_OBLIGATIONS"
        )
    elif (
        current_clock != item.validity.clock_id
        or sequence < item.validity.not_before_sequence
        or sequence > item.validity.not_after_sequence
    ):
        status = "OUTSIDE_VALIDITY_WINDOW"
        diagnostics.append("EXPLICIT_VALIDITY_WINDOW_NOT_SATISFIED")
    else:
        status = "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
        diagnostics.extend(
            (
                "AUTHORITY_REFERENCE_REQUIRES_POINT_OF_USE_REVALIDATION",
                "NO_WAIVER_OR_AUTHORIZATION_PERFORMED_BY_FOUNDATION",
                "RESULTING_OBLIGATIONS_REMAIN_OWNED_BY_EXISTING_CALCULUS",
            )
        )
    return ManualOverrideAssessment(
        override_id=item.override_id,
        override_fingerprint=item.fingerprint,
        rule_revision_id=item.rule_revision_id,
        rule_fingerprint=item.rule_fingerprint,
        accepted_risk_assessment_id=item.accepted_risk_assessment_id,
        accepted_risk_assessment_fingerprint=item.accepted_risk_assessment_fingerprint,
        status=status,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "MANUAL_OVERRIDE_CONTRACT_ID",
    "MANUAL_OVERRIDE_CONTRACT_VERSION",
    "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID",
    "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION",
    "MANUAL_OVERRIDE_STABILITY",
    "MANUAL_OVERRIDE_ASSESSMENT_STATUSES",
    "OverrideValidityWindow",
    "ResultingObligationRef",
    "ManualOverride",
    "ManualOverrideAssessment",
    "bind_manual_override",
    "evaluate_manual_override",
]
