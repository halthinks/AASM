from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .event_causality import CausalEventIdentity
from .evidence import EvidenceRecord
from .external_machine import MachineBinding, MachineStateObservation
from .observation_freshness import (
    OBSERVATION_FRESHNESS_CONTRACT_ID,
    ObservationFreshnessAssessment,
    assess_freshness,
    observation_freshness_contract,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID = "aasm.observation.freshness.runtime.v1"
OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_VERSION = "0.1.0"
OBSERVATION_FRESHNESS_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
OBSERVATION_FRESHNESS_CAPABILITIES = {"assess": "observation.freshness.assess"}

_FRESHNESS_RECORD_TYPE = "aasm_observation_freshness_record_type"
_FRESHNESS_DOCUMENT = "document"
_FRESHNESS_ASSESSMENT_RECORD = "OBSERVATION_FRESHNESS_ASSESSMENT"


def observation_freshness_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID,
        "contract_version": OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_VERSION,
        "stability": OBSERVATION_FRESHNESS_RUNTIME_STABILITY,
        "semantic_contract": observation_freshness_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(OBSERVATION_FRESHNESS_CAPABILITIES),
        "observation_source": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY",
        "claim_source": "EXISTING_DURABLE_OBSERVED_STATE_CLAIM_ONLY",
        "causal_source": "EXACT_DURABLE_CAUSAL_EVENT_ID_AND_FINGERPRINT",
        "reference_time_source": "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW",
        "freshness_mutates_observation": "NONE",
        "freshness_mutates_state_claim": "NONE",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "observation_authority_elevation": "NONE",
        "universal_admission": "NONE",
        "parallel_observation_store": "NONE",
        "parallel_truth_table": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_FRESHNESS_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("observation-freshness Evidence is missing canonical document")


def project_observation_freshness_evidence(records) -> dict[str, Any]:
    assessments: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_FRESHNESS_RECORD_TYPE) != _FRESHNESS_ASSESSMENT_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            item = ObservationFreshnessAssessment.from_dict(document)
            candidate = {"assessment": item.to_dict(), "evidence_id": evidence_id}
            prior = assessments.get(item.assessment_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"observation freshness assessment identity collision: {item.assessment_id}")
            if metadata.get("object_id") != item.assessment_id:
                raise ValueError(f"freshness metadata object_id mismatch: {item.assessment_id}")
            if metadata.get("object_fingerprint") != item.fingerprint:
                raise ValueError(f"freshness metadata fingerprint mismatch: {item.assessment_id}")
            assessments[item.assessment_id] = candidate
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": _FRESHNESS_ASSESSMENT_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": observation_freshness_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "assessments": assessments,
    }


class ObservationFreshnessRuntimeMixin:
    def observation_freshness_contract_report(self) -> dict[str, Any]:
        return observation_freshness_runtime_contract()

    def _observation_freshness_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_observation_freshness_evidence(records)

    def _require_valid_observation_freshness_projection(self) -> dict[str, Any]:
        report = self._observation_freshness_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable observation-freshness projection: {report['issues']}")
        return report

    def _authorize_observation_freshness(
        self,
        assessment: ObservationFreshnessAssessment,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("observation freshness assessment requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                assessment.workspace_id,
                assessment.scope_id,
                OBSERVATION_FRESHNESS_CAPABILITIES["assess"],
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata={
                    "assessment_id": assessment.assessment_id,
                    "observation_id": assessment.observation_id,
                    "causal_event_id": assessment.causal_event_id,
                    "status": assessment.status,
                },
            ),
            derived_from=tuple(derived_from),
            reason="observation-freshness scoped authority evaluated",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"observation-freshness denied {OBSERVATION_FRESHNESS_CAPABILITIES['assess']}: {result['decision']['reason']}"
            )
        return result

    def _record_observation_freshness_document(
        self,
        item: ObservationFreshnessAssessment,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = item.to_dict()
        identity = {
            "record_type": _FRESHNESS_ASSESSMENT_RECORD,
            "object_id": item.assessment_id,
            "document": payload,
        }
        evidence_id = f"observation-freshness-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_FRESHNESS_RECORD_TYPE) != _FRESHNESS_ASSESSMENT_RECORD
                or metadata.get(_FRESHNESS_DOCUMENT) != payload
                or metadata.get("object_id") != item.assessment_id
                or metadata.get("object_fingerprint") != item.fingerprint
            ):
                raise ValueError(f"observation-freshness Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="observation_freshness",
            statement=canonical_semantic_json(payload),
            source=OBSERVATION_FRESHNESS_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _FRESHNESS_RECORD_TYPE: _FRESHNESS_ASSESSMENT_RECORD,
                _FRESHNESS_DOCUMENT: payload,
                "object_id": item.assessment_id,
                "object_fingerprint": item.fingerprint,
                "assessed_by_principal_id": actor_principal_id,
                "authority_context_time": float(at_time),
                "freshness_reference_time_is_explicit": True,
                "authority_context_time_is_freshness_reference": False,
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "observation_authority_elevation": "NONE",
                "universal_admission": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def assess_machine_observation_freshness(
        self,
        observation_id: str,
        causal_event_id: str,
        *,
        actor_principal_id: str,
        expected_boot_epoch: int,
        reference_time_ns: int,
        reference_clock_id: str,
        max_age_ns: int,
        expected_problem_revision_id: str = "",
        expected_external_revision_id: str = "",
        minimum_source_clock_quality: str = "MONOTONIC_LOCAL",
        max_source_clock_uncertainty_ns: int | None = None,
        allow_receipt_time_fallback: bool = False,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "machine observation freshness assessed",
    ) -> dict[str, Any]:
        observation_row = self.machine_state_observation_report(str(observation_id))
        observation = MachineStateObservation.from_dict(observation_row["observation"])
        binding_row = self.machine_binding_report(observation.binding_id)
        binding = MachineBinding.from_dict(binding_row["binding"])
        state_row = self.state_claim_report(observation.state_claim_id)
        claim = StateClaim.from_dict(state_row["claim"])
        event_row = self.causal_event_report(str(causal_event_id))
        event = CausalEventIdentity.from_dict(event_row["event"])

        if event.object_kind != "MACHINE_STATE_OBSERVATION" or event.object_id != observation.observation_id:
            raise ValueError("freshness causal event does not bind the exact durable machine state observation")
        if event.event_kind != "OBSERVATION_EMITTED":
            raise ValueError("freshness causal event must be an OBSERVATION_EMITTED event")
        if event.workspace_id != claim.workspace_id or event.scope_id != claim.scope_id:
            raise ValueError("freshness causal event workspace/scope does not match observation claim")
        if event.subject_id != claim.subject_id or event.subject_id != binding.subject_id:
            raise ValueError("freshness causal event subject does not match observation")
        if event.problem_revision_id != claim.problem_revision_id:
            raise ValueError("freshness causal event problem revision does not match observation claim")
        if event.external_revision_id != observation.external_revision_id or event.external_revision_id != claim.external_revision_id:
            raise ValueError("freshness causal event external revision does not match observation")

        assessment = assess_freshness(
            event,
            workspace_id=claim.workspace_id,
            scope_id=claim.scope_id,
            subject_id=claim.subject_id,
            state_namespace=claim.state_namespace,
            observation_id=observation.observation_id,
            observation_fingerprint=observation.fingerprint,
            state_claim_id=claim.claim_id,
            state_claim_fingerprint=claim.fingerprint,
            actual_problem_revision_id=claim.problem_revision_id,
            expected_problem_revision_id=str(expected_problem_revision_id).strip(),
            actual_external_revision_id=claim.external_revision_id,
            expected_external_revision_id=str(expected_external_revision_id).strip(),
            expected_boot_epoch=expected_boot_epoch,
            reference_time_ns=reference_time_ns,
            reference_clock_id=reference_clock_id,
            max_age_ns=max_age_ns,
            minimum_source_clock_quality=minimum_source_clock_quality,
            max_source_clock_uncertainty_ns=max_source_clock_uncertainty_ns,
            allow_receipt_time_fallback=allow_receipt_time_fallback,
        )

        projection = self._require_valid_observation_freshness_projection()
        prior = projection["assessments"].get(assessment.assessment_id)
        if prior is not None:
            if prior["assessment"]["fingerprint"] != assessment.fingerprint:
                raise RuntimeError(
                    "freshness semantic collision: identical observation/event/policy inputs produced a different verdict"
                )
            return {
                **deepcopy(prior),
                "already_assessed": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "observation_authority_elevated": False,
                "universal_admission_granted": False,
            }

        lineage = self._require_evidence_ids(
            tuple(
                sorted(
                    set(
                        (
                            *map(str, evidence_ids),
                            str(observation_row["evidence_id"]),
                            str(binding_row["evidence_id"]),
                            str(state_row["evidence_id"]),
                            str(event_row["evidence_id"]),
                        )
                    )
                )
            )
        )
        authorization = self._authorize_observation_freshness(
            assessment,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_observation_freshness_document(
            assessment,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "assessment": assessment.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_assessed": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "observation_authority_elevated": False,
            "universal_admission_granted": False,
        }

    def observation_freshness_assessment_report(self, assessment_id: str) -> dict[str, Any]:
        projection = self._require_valid_observation_freshness_projection()
        try:
            return deepcopy(projection["assessments"][str(assessment_id)])
        except KeyError:
            raise KeyError(f"unknown observation freshness assessment: {assessment_id}") from None

    def observation_freshness_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_observation_freshness_projection()
        assessments: dict[str, dict[str, Any]] = {}
        for assessment_id, row in sorted(projection["assessments"].items()):
            document = row["assessment"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if status is not None and document.get("status") != status:
                continue
            assessments[assessment_id] = deepcopy(row)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "valid": True,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "status": status,
            "assessments": assessments,
            "fact_authority_creation": "NONE",
            "effect_authority": "NONE",
            "observation_authority_elevation": "NONE",
            "universal_admission": "NONE",
        }


__all__ = [
    "OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID",
    "OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_VERSION",
    "OBSERVATION_FRESHNESS_RUNTIME_STABILITY",
    "OBSERVATION_FRESHNESS_CAPABILITIES",
    "ObservationFreshnessRuntimeMixin",
    "project_observation_freshness_evidence",
    "observation_freshness_runtime_contract",
]
