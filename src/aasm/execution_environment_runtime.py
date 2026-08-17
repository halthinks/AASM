from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .calibration import CalibrationCertificate
from .evidence import EvidenceRecord
from .execution_environment import (
    EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID,
    EXECUTION_ENVIRONMENT_CONTRACT_ID,
    EnvironmentEvidenceBinding,
    ExecutionEnvironment,
    environment_level_accepted,
    execution_environment_contract,
)
from .physical_identity import PhysicalIdentity
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .source_trust import SourceTrustAssertion
from .state_authority import StateClaim


EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID = "aasm.execution.environment.runtime.v1"
EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_VERSION = "0.1.0"
EXECUTION_ENVIRONMENT_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

EXECUTION_ENVIRONMENT_CAPABILITIES = {
    "record": "execution.environment.record",
    "bind_observation": "execution.environment.bind-observation",
}

_EXECUTION_ENVIRONMENT_RECORD_TYPE = "aasm_execution_environment_record_type"
_EXECUTION_ENVIRONMENT_DOCUMENT = "document"
_ENVIRONMENT_RECORD = "EXECUTION_ENVIRONMENT"
_ENVIRONMENT_BINDING_RECORD = "ENVIRONMENT_EVIDENCE_BINDING"


def execution_environment_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID,
        "contract_version": EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_VERSION,
        "stability": EXECUTION_ENVIRONMENT_RUNTIME_STABILITY,
        "semantic_contract": execution_environment_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_BIND_NOT_ENVIRONMENT_TRUTH",
        "capabilities": deepcopy(EXECUTION_ENVIRONMENT_CAPABILITIES),
        "physical_identity_source": "EXISTING_PHYSICAL_IDENTITY_PROJECTION_ONLY",
        "calibration_source": "EXISTING_CALIBRATION_PROJECTION_ONLY",
        "source_trust_source": "EXISTING_SOURCE_TRUST_PROJECTION_ONLY",
        "observation_source": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY",
        "state_claim_source": "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY",
        "level_acceptance": "EXACT_ACCEPTED_LEVEL_SET_MEMBERSHIP_NO_ORDINAL_INFERENCE",
        "environment_level_authority": "NONE",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "source_trust_creation": "NONE",
        "observation_mutation": "NONE",
        "machine_state_mutation": "NONE",
        "parallel_environment_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_observation_store": "NONE",
        "parallel_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_EXECUTION_ENVIRONMENT_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("execution-environment Evidence is missing canonical document")


def project_execution_environment_evidence(records) -> dict[str, Any]:
    environments: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_EXECUTION_ENVIRONMENT_RECORD_TYPE)
        if record_type not in {_ENVIRONMENT_RECORD, _ENVIRONMENT_BINDING_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _ENVIRONMENT_RECORD:
                item = ExecutionEnvironment.from_dict(document)
                object_id = item.environment_id
                fingerprint = item.fingerprint
                candidate = {"environment": item.to_dict(), "evidence_id": evidence_id}
                prior = environments.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"execution environment identity collision: {object_id}")
                environments[object_id] = candidate
            else:
                item = EnvironmentEvidenceBinding.from_dict(document)
                object_id = item.binding_id
                fingerprint = item.fingerprint
                candidate = {"binding": item.to_dict(), "evidence_id": evidence_id}
                prior = bindings.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"environment binding identity collision: {object_id}")
                bindings[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"execution-environment metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"execution-environment metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })

    for binding_id, row in bindings.items():
        binding = EnvironmentEvidenceBinding.from_dict(row["binding"])
        environment_row = environments.get(binding.environment_id)
        if environment_row is None:
            issues.append({
                "index": -1,
                "evidence_id": row["evidence_id"],
                "record_type": _ENVIRONMENT_BINDING_RECORD,
                "error": f"ValueError: environment binding references unknown environment: {binding_id}",
            })
        elif environment_row["environment"]["fingerprint"] != binding.environment_fingerprint:
            issues.append({
                "index": -1,
                "evidence_id": row["evidence_id"],
                "record_type": _ENVIRONMENT_BINDING_RECORD,
                "error": f"ValueError: environment binding fingerprint mismatch: {binding_id}",
            })
    return {
        "runtime_contract": execution_environment_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "environments": environments,
        "bindings": bindings,
    }


class ExecutionEnvironmentRuntimeMixin:
    def execution_environment_contract_report(self) -> dict[str, Any]:
        return execution_environment_runtime_contract()

    def _execution_environment_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_execution_environment_evidence(records)

    def _require_valid_execution_environment_projection(self) -> dict[str, Any]:
        report = self._execution_environment_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable execution-environment projection: {report['issues']}")
        return report

    def _authorize_execution_environment_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        capability: str,
        at_time: float,
        metadata: Mapping[str, Any] | None = None,
        derived_from: Sequence[str] = (),
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("execution-environment mutation requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata=deepcopy(dict(metadata or {})),
            ),
            derived_from=tuple(derived_from),
            reason=f"execution-environment scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"execution-environment denied {capability}: {result['decision']['reason']}"
            )
        return result

    def _record_execution_environment_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"execution-environment-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_EXECUTION_ENVIRONMENT_RECORD_TYPE) != record_type
                or metadata.get(_EXECUTION_ENVIRONMENT_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"execution-environment Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="execution_environment",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _EXECUTION_ENVIRONMENT_RECORD_TYPE: record_type,
                _EXECUTION_ENVIRONMENT_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "source_trust_creation": "NONE",
                "machine_state_mutation": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def _validate_environment_reference_chain(
        self,
        item: ExecutionEnvironment,
    ) -> tuple[list[str], dict[str, Any]]:
        lineage: list[str] = []
        details: dict[str, Any] = {
            "physical_identity": None,
            "calibrations": {},
            "source_trust": None,
        }
        identity: PhysicalIdentity | None = None
        if item.physical_identity_id:
            row = self.physical_identity_report(item.physical_identity_id)
            identity = PhysicalIdentity.from_dict(row["identity"])
            if identity.fingerprint != item.physical_identity_fingerprint:
                raise ValueError("execution environment physical identity fingerprint mismatch")
            if identity.workspace_id != item.workspace_id or identity.scope_id != item.scope_id:
                raise ValueError("execution environment physical identity workspace/scope mismatch")
            if identity.subject_id != item.subject_id:
                raise ValueError("execution environment physical identity subject mismatch")
            if item.problem_revision_id and identity.problem_revision_id != item.problem_revision_id:
                raise ValueError("execution environment physical identity problem revision mismatch")
            if item.external_revision_id and identity.external_revision_id != item.external_revision_id:
                raise ValueError("execution environment physical identity external revision mismatch")
            lineage.append(str(row["evidence_id"]))
            details["physical_identity"] = identity.to_dict()

        for calibration_id, expected_fingerprint in sorted(item.calibration_bindings.items()):
            row = self.calibration_report(calibration_id, reference_time_ns=item.qualified_at_ns)
            calibration = CalibrationCertificate.from_dict(row["calibration"])
            if calibration.fingerprint != expected_fingerprint:
                raise ValueError(f"execution environment calibration fingerprint mismatch: {calibration_id}")
            if not row["active_at_reference_time"]:
                raise ValueError(f"execution environment calibration is not active at qualification time: {calibration_id}")
            if calibration.workspace_id != item.workspace_id or calibration.scope_id != item.scope_id:
                raise ValueError("execution environment calibration workspace/scope mismatch")
            if calibration.subject_id != item.subject_id:
                raise ValueError("execution environment calibration subject mismatch")
            if identity is not None and calibration.physical_identity_id != identity.identity_id:
                raise ValueError("execution environment calibration references a different physical identity")
            if item.problem_revision_id and calibration.problem_revision_id != item.problem_revision_id:
                raise ValueError("execution environment calibration problem revision mismatch")
            if item.external_revision_id and calibration.external_revision_id != item.external_revision_id:
                raise ValueError("execution environment calibration external revision mismatch")
            lineage.append(str(row["evidence_id"]))
            details["calibrations"][calibration_id] = calibration.to_dict()

        if item.source_trust_id:
            row = self.source_trust_report(item.source_trust_id, reference_time_ns=item.qualified_at_ns)
            assertion = SourceTrustAssertion.from_dict(row["assertion"])
            if assertion.fingerprint != item.source_trust_fingerprint:
                raise ValueError("execution environment source trust fingerprint mismatch")
            if not row["policy_input_effective_at_reference_time"]:
                raise ValueError("execution environment source trust is not effective at qualification time")
            if assertion.workspace_id != item.workspace_id or assertion.scope_id != item.scope_id:
                raise ValueError("execution environment source trust workspace/scope mismatch")
            if assertion.subject_id != item.subject_id:
                raise ValueError("execution environment source trust subject mismatch")
            if identity is not None and assertion.physical_identity_id and assertion.physical_identity_id != identity.identity_id:
                raise ValueError("execution environment source trust references a different physical identity")
            if item.problem_revision_id and assertion.problem_revision_id != item.problem_revision_id:
                raise ValueError("execution environment source trust problem revision mismatch")
            if item.external_revision_id and assertion.external_revision_id != item.external_revision_id:
                raise ValueError("execution environment source trust external revision mismatch")
            lineage.append(str(row["evidence_id"]))
            details["source_trust"] = assertion.to_dict()
            details["source_trust_disposition"] = row["trust_disposition"]
        return lineage, details

    def record_execution_environment(
        self,
        environment: ExecutionEnvironment | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "execution environment recorded",
    ) -> dict[str, Any]:
        item = environment if isinstance(environment, ExecutionEnvironment) else ExecutionEnvironment.from_dict(environment)
        projection = self._require_valid_execution_environment_projection()
        reference_lineage, reference_details = self._validate_environment_reference_chain(item)
        for row in projection["environments"].values():
            existing = ExecutionEnvironment.from_dict(row["environment"])
            if existing.logical_context_fingerprint == item.logical_context_fingerprint and existing.fingerprint != item.fingerprint:
                raise ValueError(
                    "execution environment changed level/instance/configuration/references under the same environment revision; advance environment/problem/external revision"
                )
        authorization = self._authorize_execution_environment_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EXECUTION_ENVIRONMENT_CAPABILITIES["record"],
            at_time=at_time,
            metadata={"environment_id": item.environment_id, "environment_level": item.environment_level},
            derived_from=tuple(evidence_ids),
        )
        prior = projection["environments"].get(item.environment_id)
        if prior is not None:
            if prior["environment"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"execution environment identity collision: {item.environment_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((*map(str, evidence_ids), *reference_lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_execution_environment_document(
            record_type=_ENVIRONMENT_RECORD,
            object_id=item.environment_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=EXECUTION_ENVIRONMENT_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "environment": item.to_dict(),
            "reference_details": reference_details,
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "source_trust_created": False,
            "claim_admitted": False,
        }

    def bind_machine_observation_environment(
        self,
        observation_id: str,
        environment_id: str,
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "machine observation execution environment bound",
    ) -> dict[str, Any]:
        projection = self._require_valid_execution_environment_projection()
        try:
            environment_row = deepcopy(projection["environments"][environment_id])
        except KeyError:
            raise KeyError(f"unknown execution environment: {environment_id}") from None
        environment = ExecutionEnvironment.from_dict(environment_row["environment"])
        observation_row = self.machine_state_observation_report(observation_id)
        observation = deepcopy(observation_row["observation"])
        state_row = self.state_claim_report(observation["state_claim_id"])
        claim = StateClaim.from_dict(state_row["claim"])
        if claim.workspace_id != environment.workspace_id or claim.scope_id != environment.scope_id:
            raise ValueError("environment binding observation workspace/scope mismatch")
        if claim.subject_id != environment.subject_id:
            raise ValueError("environment binding observation subject mismatch")
        if environment.problem_revision_id and claim.problem_revision_id != environment.problem_revision_id:
            raise ValueError("environment binding observation problem revision mismatch")
        if environment.external_revision_id and claim.external_revision_id != environment.external_revision_id:
            raise ValueError("environment binding observation external revision mismatch")
        item = EnvironmentEvidenceBinding(
            workspace_id=environment.workspace_id,
            scope_id=environment.scope_id,
            subject_id=environment.subject_id,
            environment_id=environment.environment_id,
            environment_fingerprint=environment.fingerprint,
            object_kind="MACHINE_STATE_OBSERVATION",
            object_id=str(observation["observation_id"]),
            object_fingerprint=str(observation["fingerprint"]),
            problem_revision_id=claim.problem_revision_id,
            external_revision_id=claim.external_revision_id,
        )
        authorization = self._authorize_execution_environment_action(
            actor_principal_id=actor_principal_id,
            workspace_id=environment.workspace_id,
            scope_id=environment.scope_id,
            capability=EXECUTION_ENVIRONMENT_CAPABILITIES["bind_observation"],
            at_time=at_time,
            metadata={
                "environment_id": environment.environment_id,
                "binding_id": item.binding_id,
                "observation_id": observation_id,
            },
            derived_from=tuple(evidence_ids),
        )
        prior = projection["bindings"].get(item.binding_id)
        if prior is not None:
            if prior["binding"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"environment binding identity collision: {item.binding_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((
            str(environment_row["evidence_id"]),
            str(observation_row["evidence_id"]),
            str(state_row["evidence_id"]),
            str(authorization["evidence_id"]),
            *map(str, evidence_ids),
        ))))
        evidence_id = self._record_execution_environment_document(
            record_type=_ENVIRONMENT_BINDING_RECORD,
            object_id=item.binding_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "binding": item.to_dict(),
            "environment": environment.to_dict(),
            "observation": observation,
            "state_claim": claim.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "observation_mutated": False,
        }

    def execution_environment_report(
        self,
        environment_id: str,
        *,
        reference_time_ns: int | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_execution_environment_projection()
        try:
            row = deepcopy(projection["environments"][environment_id])
        except KeyError:
            raise KeyError(f"unknown execution environment: {environment_id}") from None
        environment = ExecutionEnvironment.from_dict(row["environment"])
        reference_time = environment.qualified_at_ns if reference_time_ns is None else reference_time_ns
        calibrations_active = True
        calibration_status: dict[str, bool] = {}
        trust_effective: bool | None = None
        trust_disposition: str | None = None
        if environment.calibration_bindings:
            for calibration_id, expected_fingerprint in sorted(environment.calibration_bindings.items()):
                calibration_row = self.calibration_report(calibration_id, reference_time_ns=reference_time)
                calibration_status[calibration_id] = bool(
                    calibration_row["calibration"]["fingerprint"] == expected_fingerprint
                    and calibration_row["active_at_reference_time"]
                )
            calibrations_active = all(calibration_status.values())
        if environment.source_trust_id:
            trust_row = self.source_trust_report(environment.source_trust_id, reference_time_ns=reference_time)
            trust_effective = bool(
                trust_row["assertion"]["fingerprint"] == environment.source_trust_fingerprint
                and trust_row["policy_input_effective_at_reference_time"]
            )
            trust_disposition = str(trust_row["trust_disposition"])
        references_effective = calibrations_active and (trust_effective is not False)
        return {
            **row,
            "reference_time_ns": reference_time,
            "calibration_status": calibration_status,
            "required_calibrations_active": calibrations_active,
            "source_trust_effective": trust_effective,
            "source_trust_disposition": trust_disposition,
            "qualification_references_effective_at_reference_time": references_effective,
            "environment_level_is_authority_rank": False,
            "fact_authority_granted": False,
            "effect_authority_granted": False,
            "source_trust_granted": False,
        }

    def execution_environment_binding_report(
        self,
        binding_id: str,
        *,
        accepted_levels: Sequence[str] = (),
        reference_time_ns: int | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_execution_environment_projection()
        try:
            row = deepcopy(projection["bindings"][binding_id])
        except KeyError:
            raise KeyError(f"unknown execution environment binding: {binding_id}") from None
        binding = EnvironmentEvidenceBinding.from_dict(row["binding"])
        environment_report = self.execution_environment_report(
            binding.environment_id,
            reference_time_ns=reference_time_ns,
        )
        environment = ExecutionEnvironment.from_dict(environment_report["environment"])
        accepted = None if not accepted_levels else environment_level_accepted(environment.environment_level, accepted_levels)
        return {
            **row,
            "environment": environment.to_dict(),
            "environment_level": environment.environment_level,
            "accepted_levels": list(dict.fromkeys(map(str, accepted_levels))),
            "environment_level_accepted": accepted,
            "qualification_references_effective_at_reference_time": environment_report["qualification_references_effective_at_reference_time"],
            "environment_level_is_authority_rank": False,
            "fact_authority_granted": False,
            "effect_authority_granted": False,
        }

    def execution_environments_report(self, *, reference_time_ns: int | None = None) -> dict[str, Any]:
        projection = self._require_valid_execution_environment_projection()
        return {
            "runtime_contract": execution_environment_runtime_contract(),
            "valid": True,
            "environments": {
                environment_id: self.execution_environment_report(environment_id, reference_time_ns=reference_time_ns)
                for environment_id in sorted(projection["environments"])
            },
            "bindings": deepcopy(projection["bindings"]),
            "parallel_environment_store": "NONE_EVIDENCE_PROJECTION_ONLY",
            "parallel_truth_table": "NONE",
        }


__all__ = [
    "EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_RUNTIME_STABILITY",
    "EXECUTION_ENVIRONMENT_CAPABILITIES",
    "ExecutionEnvironmentRuntimeMixin",
    "project_execution_environment_evidence",
    "execution_environment_runtime_contract",
]
