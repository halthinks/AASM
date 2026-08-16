from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .external_machine import (
    MACHINE_BINDING_CONTRACT_ID,
    MACHINE_STATE_OBSERVATION_CONTRACT_ID,
    MachineBinding,
    MachineStateObservation,
    external_machine_contract,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID = "aasm.machine.external.runtime.v1"
EXTERNAL_MACHINE_RUNTIME_CONTRACT_VERSION = "0.1.0"
EXTERNAL_MACHINE_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

EXTERNAL_MACHINE_CAPABILITIES = {
    "binding_register": "machine.binding.register",
    "observation_record": "machine.observation.record",
}

_EXTERNAL_MACHINE_RECORD_TYPE = "aasm_external_machine_record_type"
_EXTERNAL_MACHINE_DOCUMENT = "document"
_MACHINE_BINDING_RECORD = "MACHINE_BINDING"
_MACHINE_OBSERVATION_RECORD = "MACHINE_STATE_OBSERVATION"


def external_machine_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID,
        "contract_version": EXTERNAL_MACHINE_RUNTIME_CONTRACT_VERSION,
        "stability": EXTERNAL_MACHINE_RUNTIME_STABILITY,
        "semantic_contract": external_machine_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(EXTERNAL_MACHINE_CAPABILITIES),
        "observer_capability_validation": "EXISTING_AASM_CAPABILITY_ABI_OBSERVER_REQUIRED",
        "executor_capability_validation": "EXISTING_AASM_CAPABILITY_ABI_OPERATOR_REQUIRED",
        "state_observation_source": "EXISTING_PR1_DURABLE_OBSERVED_STATE_CLAIM",
        "external_state_table": "NONE",
        "binding_grants_fact_authority": False,
        "binding_grants_effect_authority": False,
        "capability_reference_grants_authority": False,
        "observation_grants_fact_authority": False,
        "executor_invocation": "NONE",
        "effect_dispatch": "NONE",
        "machine_state_mutation": "NONE",
        "postcondition_verification": "NOT_IMPLEMENTED_PR2A",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_EXTERNAL_MACHINE_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("external-machine Evidence is missing canonical document")


def project_external_machine_evidence(records) -> dict[str, Any]:
    bindings: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_EXTERNAL_MACHINE_RECORD_TYPE)
        if record_type not in {_MACHINE_BINDING_RECORD, _MACHINE_OBSERVATION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _MACHINE_BINDING_RECORD:
                item = MachineBinding.from_dict(document)
                object_id = item.binding_id
                fingerprint = item.fingerprint
                candidate = {"binding": item.to_dict(), "evidence_id": evidence_id}
                prior = bindings.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"machine binding identity collision: {object_id}")
                bindings[object_id] = candidate
            else:
                item = MachineStateObservation.from_dict(document)
                object_id = item.observation_id
                fingerprint = item.fingerprint
                candidate = {"observation": item.to_dict(), "evidence_id": evidence_id}
                prior = observations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"machine state observation identity collision: {object_id}")
                observations[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"external-machine metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"external-machine metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for observation_id, row in observations.items():
        binding_id = row["observation"].get("binding_id")
        if binding_id not in bindings:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _MACHINE_OBSERVATION_RECORD,
                    "error": f"ValueError: observation references unknown machine binding: {observation_id}",
                }
            )

    return {
        "runtime_contract": external_machine_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "bindings": bindings,
        "observations": observations,
    }


class ExternalMachineRuntimeMixin:
    def external_machine_contract_report(self) -> dict[str, Any]:
        return external_machine_runtime_contract()

    def _external_machine_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_external_machine_evidence(records)

    def _require_valid_external_machine_projection(self) -> dict[str, Any]:
        report = self._external_machine_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable external-machine projection: {report['issues']}")
        return report

    def _authorize_external_machine_action(
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
            raise PermissionError("external-machine mutation requires actor_principal_id")
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
            reason=f"external-machine scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"external-machine denied {capability}: {result['decision']['reason']}")
        return result

    def _validate_machine_capability_reference(self, capability_id: str, expected_type: str) -> dict[str, Any]:
        try:
            report = self.capability_report(capability_id)
        except KeyError:
            raise KeyError(f"unknown machine capability reference: {capability_id}") from None
        contract = deepcopy(report["capability"]["contract"])
        if contract.get("capability_type") != expected_type:
            raise ValueError(
                f"machine capability {capability_id} must be {expected_type}, got {contract.get('capability_type')}"
            )
        return report

    def _record_external_machine_document(
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
        evidence_id = f"external-machine-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_EXTERNAL_MACHINE_RECORD_TYPE) != record_type
                or metadata.get(_EXTERNAL_MACHINE_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"external-machine Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="external_machine",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _EXTERNAL_MACHINE_RECORD_TYPE: record_type,
                _EXTERNAL_MACHINE_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "external_state_table": "NONE",
                "fact_authority": "NONE_GRANTED",
                "effect_authority": "NONE_GRANTED",
                "executor_invocation": "NONE",
                "machine_state_mutation": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def register_machine_binding(
        self,
        binding: MachineBinding | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "external machine binding registered",
    ) -> dict[str, Any]:
        item = binding if isinstance(binding, MachineBinding) else MachineBinding.from_dict(binding)
        self._validate_machine_capability_reference(item.observer_capability_id, "OBSERVER")
        self._validate_machine_capability_reference(item.executor_capability_id, "OPERATOR")
        if item.fact_authority_ids:
            authorities = self.state_authority_report(at_time=at_time)["authorities"]
            missing = [authority_id for authority_id in item.fact_authority_ids if authority_id not in authorities]
            if missing:
                raise KeyError(f"unknown fact authority references in machine binding: {missing}")
        authorization = self._authorize_external_machine_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EXTERNAL_MACHINE_CAPABILITIES["binding_register"],
            at_time=at_time,
            metadata={
                "binding_id": item.binding_id,
                "external_machine_id": item.external_machine_id,
                "observer_capability_id": item.observer_capability_id,
                "executor_capability_id": item.executor_capability_id,
            },
            derived_from=evidence_ids,
        )
        projection = self._require_valid_external_machine_projection()
        prior = projection["bindings"].get(item.binding_id)
        if prior is not None:
            if prior["binding"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"machine binding identity collision: {item.binding_id}")
            return {**deepcopy(prior), "already_registered": True}
        lineage = tuple(sorted(set((*map(str, evidence_ids), str(authorization["evidence_id"])))))
        evidence_id = self._record_external_machine_document(
            record_type=_MACHINE_BINDING_RECORD,
            object_id=item.binding_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=MACHINE_BINDING_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "binding": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_registered": False,
        }

    def record_machine_state_observation(
        self,
        observation: MachineStateObservation | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        reason: str = "external machine state observation recorded",
    ) -> dict[str, Any]:
        item = observation if isinstance(observation, MachineStateObservation) else MachineStateObservation.from_dict(observation)
        if actor_principal_id != item.observer_principal_id:
            raise PermissionError("machine observation actor must equal observer_principal_id")
        projection = self._require_valid_external_machine_projection()
        try:
            binding_row = deepcopy(projection["bindings"][item.binding_id])
        except KeyError:
            raise KeyError(f"unknown machine binding: {item.binding_id}") from None
        binding = MachineBinding.from_dict(binding_row["binding"])
        if item.observer_capability_id != binding.observer_capability_id:
            raise ValueError("machine observation capability does not match binding observer capability")
        self._validate_machine_capability_reference(item.observer_capability_id, "OBSERVER")
        if item.external_revision_id != binding.external_revision_id:
            raise ValueError("machine observation external revision does not match binding")

        state_row = self.state_claim_report(item.state_claim_id)
        claim = StateClaim.from_dict(state_row["claim"])
        if claim.claim_kind != "OBSERVED":
            raise ValueError("machine state observation requires a durable OBSERVED state claim")
        if claim.source_principal_id != item.observer_principal_id:
            raise ValueError("machine observation principal does not match source state claim")
        if claim.workspace_id != binding.workspace_id or claim.scope_id != binding.scope_id:
            raise ValueError("machine observation workspace/scope does not match binding")
        if claim.subject_id != binding.subject_id:
            raise ValueError("machine observation subject does not match binding")
        if claim.state_namespace not in binding.state_namespaces:
            raise ValueError("machine observation state namespace is not supported by binding")
        if claim.external_revision_id != binding.external_revision_id:
            raise ValueError("machine observation source claim external revision does not match binding")
        if binding.problem_revision_id and claim.problem_revision_id != binding.problem_revision_id:
            raise ValueError("machine observation source claim problem revision does not match binding")

        authorization = self._authorize_external_machine_action(
            actor_principal_id=actor_principal_id,
            workspace_id=binding.workspace_id,
            scope_id=binding.scope_id,
            capability=EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
            at_time=at_time,
            metadata={
                "binding_id": binding.binding_id,
                "observation_id": item.observation_id,
                "state_claim_id": claim.claim_id,
            },
            derived_from=(state_row["evidence_id"],),
        )
        prior = projection["observations"].get(item.observation_id)
        if prior is not None:
            if prior["observation"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"machine state observation identity collision: {item.observation_id}")
            return {**deepcopy(prior), "already_recorded": True}

        lineage = tuple(
            sorted(
                {
                    str(binding_row["evidence_id"]),
                    str(state_row["evidence_id"]),
                    str(authorization["evidence_id"]),
                }
            )
        )
        evidence_id = self._record_external_machine_document(
            record_type=_MACHINE_OBSERVATION_RECORD,
            object_id=item.observation_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=MACHINE_STATE_OBSERVATION_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "observation": item.to_dict(),
            "state_claim": claim.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_granted": False,
            "effect_authority_granted": False,
            "executor_invoked": False,
        }

    def machine_binding_report(self, binding_id: str) -> dict[str, Any]:
        projection = self._require_valid_external_machine_projection()
        try:
            return deepcopy(projection["bindings"][binding_id])
        except KeyError:
            raise KeyError(f"unknown machine binding: {binding_id}") from None

    def machine_state_observation_report(self, observation_id: str) -> dict[str, Any]:
        projection = self._require_valid_external_machine_projection()
        try:
            return deepcopy(projection["observations"][observation_id])
        except KeyError:
            raise KeyError(f"unknown machine state observation: {observation_id}") from None

    def external_machine_report(self, binding_id: str | None = None) -> dict[str, Any]:
        projection = self._require_valid_external_machine_projection()
        if binding_id is None:
            bindings = deepcopy(projection["bindings"])
            observations = deepcopy(projection["observations"])
        else:
            if binding_id not in projection["bindings"]:
                raise KeyError(f"unknown machine binding: {binding_id}")
            bindings = {binding_id: deepcopy(projection["bindings"][binding_id])}
            observations = {
                observation_id: deepcopy(row)
                for observation_id, row in projection["observations"].items()
                if row["observation"]["binding_id"] == binding_id
            }
        return {
            "runtime_contract": external_machine_runtime_contract(),
            "valid": True,
            "bindings": bindings,
            "observations": observations,
            "external_state_table": "NONE",
            "fact_authority": "NONE_GRANTED",
            "effect_authority": "NONE_GRANTED",
            "executor_invocation": "NONE",
            "effect_dispatch": "NONE",
            "machine_state_mutation": "NONE",
            "postcondition_verification": "NOT_IMPLEMENTED_PR2A",
        }


__all__ = [
    "EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID",
    "EXTERNAL_MACHINE_RUNTIME_CONTRACT_VERSION",
    "EXTERNAL_MACHINE_RUNTIME_STABILITY",
    "EXTERNAL_MACHINE_CAPABILITIES",
    "ExternalMachineRuntimeMixin",
    "project_external_machine_evidence",
    "external_machine_runtime_contract",
]
