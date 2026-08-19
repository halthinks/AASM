from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint
from ._safety_envelope_common import (
    CONSTRAINT_RELATIONS, SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID,
    SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION, SAFETY_ENVELOPE_ASSESSMENT_STATUSES,
    _optional, _required, _sha256, _uniq,
)

@dataclass(frozen=True)
class SafetyConstraintAssessment:
    constraint_id: str
    variable_id: str
    relation: str
    rule_revision_id: str
    rule_fingerprint: str
    allowed_quantity_id: str
    allowed_quantity_fingerprint: str
    observed_quantity_id: str = ""
    observed_quantity_fingerprint: str = ""
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "constraint_id",
            "variable_id",
            "rule_revision_id",
            "allowed_quantity_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        relation = _required("constraint relation", self.relation).upper()
        if relation not in CONSTRAINT_RELATIONS:
            raise ValueError(f"unsupported safety constraint relation: {relation}")
        object.__setattr__(self, "relation", relation)
        object.__setattr__(
            self, "rule_fingerprint", _sha256("rule_fingerprint", self.rule_fingerprint)
        )
        object.__setattr__(
            self,
            "allowed_quantity_fingerprint",
            _sha256("allowed_quantity_fingerprint", self.allowed_quantity_fingerprint),
        )
        observed_id = _optional(self.observed_quantity_id)
        observed_fingerprint = _optional(self.observed_quantity_fingerprint)
        if bool(observed_id) != bool(observed_fingerprint):
            raise ValueError(
                "safety constraint assessment observed quantity ID and fingerprint must both be present or absent"
            )
        if observed_fingerprint:
            observed_fingerprint = _sha256(
                "observed_quantity_fingerprint", observed_fingerprint
            )
        if relation in {"WITHIN", "OUTSIDE", "OVERLAPS_BOUNDARY", "UNSUPPORTED"} and not observed_id:
            raise ValueError(
                f"safety constraint relation {relation} requires an observed quantity identity"
            )
        object.__setattr__(self, "observed_quantity_id", observed_id)
        object.__setattr__(self, "observed_quantity_fingerprint", observed_fingerprint)
        object.__setattr__(
            self,
            "diagnostics",
            _uniq(self.diagnostics, name="constraint diagnostic"),
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "variable_id": self.variable_id,
            "relation": self.relation,
            "rule_revision_id": self.rule_revision_id,
            "rule_fingerprint": self.rule_fingerprint,
            "allowed_quantity_id": self.allowed_quantity_id,
            "allowed_quantity_fingerprint": self.allowed_quantity_fingerprint,
            "observed_quantity_id": self.observed_quantity_id,
            "observed_quantity_fingerprint": self.observed_quantity_fingerprint,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SafetyConstraintAssessment":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("safety constraint assessment fingerprint mismatch")
        return item


@dataclass(frozen=True)
class SafetyEnvelopeAssessment:
    envelope_id: str
    envelope_fingerprint: str
    hybrid_state_id: str
    hybrid_state_fingerprint: str
    mode_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    status: str
    constraint_assessments: tuple[SafetyConstraintAssessment | Mapping[str, Any], ...]
    violating_constraint_ids: tuple[str, ...] = ()
    indeterminate_constraint_ids: tuple[str, ...] = ()
    missing_variable_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    fact_authority_granted: bool = False
    physical_state_authority_granted: bool = False
    effect_authority_granted: bool = False
    operational_mode_activated: bool = False
    artifact_acceptance_granted: bool = False
    dispatch_performed: bool = False
    solver_executed: bool = False
    dynamics_integrated: bool = False
    assessment_id: str = ""
    contract_id: str = SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID
    contract_version: str = SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID
            or self.contract_version != SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_VERSION
        ):
            raise ValueError("unsupported safety-envelope assessment contract")
        for name in (
            "envelope_id",
            "hybrid_state_id",
            "mode_id",
            "problem_revision_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in (
            "envelope_fingerprint",
            "hybrid_state_fingerprint",
            "problem_revision_fingerprint",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        status = _required("assessment status", self.status).upper()
        if status not in SAFETY_ENVELOPE_ASSESSMENT_STATUSES:
            raise ValueError(f"unsupported safety envelope assessment status: {status}")
        assessments = tuple(
            value
            if isinstance(value, SafetyConstraintAssessment)
            else SafetyConstraintAssessment.from_dict(value)
            for value in self.constraint_assessments
        )
        ids = [value.constraint_id for value in assessments]
        if len(ids) != len(set(ids)):
            raise ValueError("safety envelope assessment constraint IDs must be unique")
        assessments = tuple(sorted(assessments, key=lambda value: value.constraint_id))
        violating = _uniq(
            self.violating_constraint_ids, name="violating constraint_id"
        )
        indeterminate = _uniq(
            self.indeterminate_constraint_ids, name="indeterminate constraint_id"
        )
        missing = _uniq(self.missing_variable_ids, name="missing variable_id")
        diagnostics = _uniq(self.diagnostics, name="assessment diagnostic")
        relation_by_id = {value.constraint_id: value.relation for value in assessments}
        expected_missing = {
            value.variable_id
            for value in assessments
            if "MISSING_OBSERVATION" in value.diagnostics
        }
        if set(missing) != expected_missing:
            raise ValueError(
                "missing variable IDs must exactly match MISSING_OBSERVATION constraint diagnostics"
            )
        if set(violating) != {
            key for key, relation in relation_by_id.items() if relation == "OUTSIDE"
        }:
            raise ValueError(
                "violating constraint IDs must exactly match OUTSIDE constraint assessments"
            )
        expected_indeterminate = {
            key
            for key, relation in relation_by_id.items()
            if relation in {"OVERLAPS_BOUNDARY", "UNKNOWN", "UNSUPPORTED"}
        }
        if set(indeterminate) != expected_indeterminate:
            raise ValueError(
                "indeterminate constraint IDs must exactly match non-decisive constraint assessments"
            )
        if status == "SATISFIED" and (
            any(value.relation != "WITHIN" for value in assessments) or not assessments
        ):
            raise ValueError("SATISFIED safety assessment requires every constraint WITHIN")
        if status == "VIOLATED" and not violating:
            raise ValueError("VIOLATED safety assessment requires an OUTSIDE constraint")
        if status == "INDETERMINATE" and (violating or not indeterminate):
            raise ValueError(
                "INDETERMINATE safety assessment requires no violation and at least one non-decisive constraint"
            )
        if status == "MODE_UNCOVERED" and assessments:
            raise ValueError("MODE_UNCOVERED safety assessment cannot carry constraint assessments")
        for name in (
            "fact_authority_granted",
            "physical_state_authority_granted",
            "effect_authority_granted",
            "operational_mode_activated",
            "artifact_acceptance_granted",
            "dispatch_performed",
            "solver_executed",
            "dynamics_integrated",
        ):
            if bool(getattr(self, name)):
                raise ValueError(f"safety envelope assessment cannot set {name}=True")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "constraint_assessments", assessments)
        object.__setattr__(self, "violating_constraint_ids", violating)
        object.__setattr__(self, "indeterminate_constraint_ids", indeterminate)
        object.__setattr__(self, "missing_variable_ids", missing)
        object.__setattr__(self, "diagnostics", diagnostics)
        derived = f"safety-envelope-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError("safety envelope assessment_id does not match canonical identity")
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_id": self.envelope_id,
            "envelope_fingerprint": self.envelope_fingerprint,
            "hybrid_state_id": self.hybrid_state_id,
            "hybrid_state_fingerprint": self.hybrid_state_fingerprint,
            "mode_id": self.mode_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "status": self.status,
            "constraint_assessments": [
                value.identity_payload() for value in self.constraint_assessments
            ],
            "violating_constraint_ids": list(self.violating_constraint_ids),
            "indeterminate_constraint_ids": list(self.indeterminate_constraint_ids),
            "missing_variable_ids": list(self.missing_variable_ids),
            "diagnostics": list(self.diagnostics),
            "fact_authority_granted": False,
            "physical_state_authority_granted": False,
            "effect_authority_granted": False,
            "operational_mode_activated": False,
            "artifact_acceptance_granted": False,
            "dispatch_performed": False,
            "solver_executed": False,
            "dynamics_integrated": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "envelope_id": self.envelope_id,
            "envelope_fingerprint": self.envelope_fingerprint,
            "hybrid_state_id": self.hybrid_state_id,
            "hybrid_state_fingerprint": self.hybrid_state_fingerprint,
            "mode_id": self.mode_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "status": self.status,
            "constraint_assessments": [
                value.to_dict() for value in self.constraint_assessments
            ],
            "violating_constraint_ids": list(self.violating_constraint_ids),
            "indeterminate_constraint_ids": list(self.indeterminate_constraint_ids),
            "missing_variable_ids": list(self.missing_variable_ids),
            "diagnostics": list(self.diagnostics),
            "fact_authority_granted": False,
            "physical_state_authority_granted": False,
            "effect_authority_granted": False,
            "operational_mode_activated": False,
            "artifact_acceptance_granted": False,
            "dispatch_performed": False,
            "solver_executed": False,
            "dynamics_integrated": False,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SafetyEnvelopeAssessment":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        for name in (
            "constraint_assessments",
            "violating_constraint_ids",
            "indeterminate_constraint_ids",
            "missing_variable_ids",
            "diagnostics",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("safety envelope assessment fingerprint mismatch")
        return item


