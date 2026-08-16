from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .effects import EffectStatus
from .evidence import EvidenceRecord
from .external_machine import MachineBinding, MachineStateObservation
from .external_machine_postcondition import (
    MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID,
    MachinePostconditionVerification,
    machine_postcondition_verification_contract,
)
from .external_machine_transition import MachineTransitionIntent
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID = "aasm.machine.postcondition-verification.runtime.v1"
MACHINE_POSTCONDITION_RUNTIME_CONTRACT_VERSION = "0.1.0"
MACHINE_POSTCONDITION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

MACHINE_POSTCONDITION_CAPABILITIES = {
    "verify": "machine.postcondition.verify",
}

_MACHINE_POSTCONDITION_RECORD_TYPE = "aasm_machine_postcondition_record_type"
_MACHINE_POSTCONDITION_DOCUMENT = "document"
_MACHINE_POSTCONDITION_VERIFICATION_RECORD = "MACHINE_POSTCONDITION_VERIFICATION"


def machine_postcondition_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID,
        "contract_version": MACHINE_POSTCONDITION_RUNTIME_CONTRACT_VERSION,
        "stability": MACHINE_POSTCONDITION_RUNTIME_STABILITY,
        "semantic_contract": machine_postcondition_verification_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(MACHINE_POSTCONDITION_CAPABILITIES),
        "effect_source": "EXISTING_AASM_EFFECT_RECORD_ONLY",
        "transition_source": "EXISTING_PR2B_MACHINE_TRANSITION_ONLY",
        "target_source": "EXISTING_PR2B_DESIRED_STATE_CLAIMS_ONLY",
        "achieved_source": "EXISTING_PR1_AUTHORITATIVE_STATE_CLAIMS_ONLY",
        "observation_source": "EXISTING_PR2A_MACHINE_STATE_OBSERVATIONS_ONLY",
        "effect_status_mutation": "NONE",
        "state_claim_creation": "NONE",
        "fact_authority_creation": "NONE",
        "machine_state_mutation": "NONE",
        "effect_authority": "NONE",
        "parallel_truth_table": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "unknown_effect": "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION",
        "command_success_is_achievement": False,
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_MACHINE_POSTCONDITION_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("machine-postcondition Evidence is missing canonical document")


def project_machine_postcondition_evidence(records) -> dict[str, Any]:
    verifications: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_MACHINE_POSTCONDITION_RECORD_TYPE) != _MACHINE_POSTCONDITION_VERIFICATION_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            item = MachinePostconditionVerification.from_dict(_document(row))
            if metadata.get("object_id") != item.verification_id:
                raise ValueError(f"machine-postcondition metadata object_id mismatch: {item.verification_id}")
            if metadata.get("object_fingerprint") != item.fingerprint:
                raise ValueError(f"machine-postcondition metadata fingerprint mismatch: {item.verification_id}")
            candidate = {"verification": item.to_dict(), "evidence_id": evidence_id}
            prior = verifications.get(item.verification_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"machine postcondition verification identity collision: {item.verification_id}")
            verifications[item.verification_id] = candidate
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": _MACHINE_POSTCONDITION_VERIFICATION_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": machine_postcondition_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "verifications": verifications,
    }


def _canonical_value(value: Any) -> str:
    return canonical_semantic_json({"value": deepcopy(value)})


class MachinePostconditionRuntimeMixin:
    def machine_postcondition_contract_report(self) -> dict[str, Any]:
        return machine_postcondition_runtime_contract()

    def _machine_postcondition_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_machine_postcondition_evidence(records)

    def _require_valid_machine_postcondition_projection(self) -> dict[str, Any]:
        report = self._machine_postcondition_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable machine-postcondition projection: {report['issues']}")
        return report

    def _record_machine_postcondition_verification(
        self,
        item: MachinePostconditionVerification,
        *,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = item.to_dict()
        evidence_id = f"machine-postcondition-evidence-{semantic_fingerprint(payload)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_MACHINE_POSTCONDITION_RECORD_TYPE) != _MACHINE_POSTCONDITION_VERIFICATION_RECORD
                or metadata.get(_MACHINE_POSTCONDITION_DOCUMENT) != payload
                or metadata.get("object_id") != item.verification_id
                or metadata.get("object_fingerprint") != item.fingerprint
            ):
                raise ValueError(f"machine-postcondition Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="machine_postcondition_verification",
            statement=canonical_semantic_json(payload),
            source=MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _MACHINE_POSTCONDITION_RECORD_TYPE: _MACHINE_POSTCONDITION_VERIFICATION_RECORD,
                _MACHINE_POSTCONDITION_DOCUMENT: payload,
                "object_id": item.verification_id,
                "object_fingerprint": item.fingerprint,
                "effect_status_mutation": "NONE",
                "state_claim_creation": "NONE",
                "fact_authority_creation": "NONE",
                "machine_state_mutation": "NONE",
                "effect_authority": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def _validated_postcondition_observations(
        self,
        *,
        binding: MachineBinding,
        observation_ids: Sequence[str],
    ) -> tuple[dict[str, tuple[MachineStateObservation, StateClaim, dict[str, Any]]], set[str]]:
        by_claim_id: dict[str, tuple[MachineStateObservation, StateClaim, dict[str, Any]]] = {}
        evidence_ids: set[str] = set()
        for observation_id in tuple(sorted(set(map(str, observation_ids)))):
            row = self.machine_state_observation_report(observation_id)
            item = MachineStateObservation.from_dict(row["observation"])
            if item.binding_id != binding.binding_id:
                raise ValueError("postcondition observation binding does not match transition binding")
            if item.external_revision_id != binding.external_revision_id:
                raise ValueError("postcondition observation external revision does not match transition binding")
            state_row = self.state_claim_report(item.state_claim_id)
            claim = StateClaim.from_dict(state_row["claim"])
            if claim.claim_kind != "OBSERVED":
                raise ValueError("postcondition machine observation must reference OBSERVED state claim")
            if claim.workspace_id != binding.workspace_id or claim.scope_id != binding.scope_id:
                raise ValueError("postcondition observed claim workspace/scope does not match binding")
            if claim.subject_id != binding.subject_id:
                raise ValueError("postcondition observed claim subject does not match binding")
            if claim.state_namespace not in binding.state_namespaces:
                raise ValueError("postcondition observed claim namespace is not supported by binding")
            if claim.external_revision_id != binding.external_revision_id:
                raise ValueError("postcondition observed claim external revision does not match binding")
            if binding.problem_revision_id and claim.problem_revision_id != binding.problem_revision_id:
                raise ValueError("postcondition observed claim problem revision does not match binding")
            by_claim_id[claim.claim_id] = (item, claim, row)
            evidence_ids.add(str(row["evidence_id"]))
            evidence_ids.add(str(state_row["evidence_id"]))
        if not by_claim_id:
            raise ValueError("postcondition verification requires at least one machine state observation")
        return by_claim_id, evidence_ids

    def verify_machine_transition_postconditions(
        self,
        transition_id: str,
        *,
        achieved_state_claim_ids: Sequence[str],
        machine_observation_ids: Sequence[str],
        verifier_principal_id: str,
        at_time: float = 0.0,
        metadata: Mapping[str, Any] | None = None,
        reason: str = "machine transition postconditions verified",
    ) -> dict[str, Any]:
        transition_row = self.machine_transition_report(transition_id)
        transition = MachineTransitionIntent.from_dict(transition_row["transition"])
        binding_row = self.machine_binding_report(transition.binding_id)
        binding = MachineBinding.from_dict(binding_row["binding"])
        effect = self.store.load_effect(self.snapshot.machine_id, transition.effect_id)

        if effect.status == EffectStatus.UNKNOWN.value:
            raise ValueError("machine transition effect is UNKNOWN; use existing effect reconciliation before postcondition verification")
        if effect.status != EffectStatus.SUCCEEDED.value:
            raise ValueError(
                f"machine transition effect must be SUCCEEDED before postcondition verification, got {effect.status}"
            )

        authorization = self._authorize_external_machine_action(
            actor_principal_id=verifier_principal_id,
            workspace_id=transition.workspace_id,
            scope_id=transition.scope_id,
            capability=MACHINE_POSTCONDITION_CAPABILITIES["verify"],
            at_time=at_time,
            metadata={"transition_id": transition.transition_id, "effect_id": transition.effect_id},
            derived_from=tuple(effect.evidence),
        )

        observed_by_claim_id, observation_evidence = self._validated_postcondition_observations(
            binding=binding,
            observation_ids=machine_observation_ids,
        )

        targets: dict[str, tuple[StateClaim, dict[str, Any]]] = {}
        lineage: set[str] = {
            str(transition_row["evidence_id"]),
            str(binding_row["evidence_id"]),
            str(authorization["evidence_id"]),
            *map(str, effect.evidence),
            *observation_evidence,
        }
        for claim_id in transition.target_state_claim_ids:
            row = self.state_claim_report(claim_id)
            claim = StateClaim.from_dict(row["claim"])
            if claim.claim_kind != "DESIRED":
                raise RuntimeError("durable machine transition target is no longer DESIRED")
            targets[claim.state_namespace] = (claim, row)
            lineage.add(str(row["evidence_id"]))

        achieved: dict[str, tuple[StateClaim, dict[str, Any]]] = {}
        for claim_id in tuple(sorted(set(map(str, achieved_state_claim_ids)))):
            row = self.state_claim_report(claim_id)
            claim = StateClaim.from_dict(row["claim"])
            if claim.claim_kind != "AUTHORITATIVE":
                raise ValueError("postcondition achieved state requires AUTHORITATIVE state claim")
            if claim.workspace_id != binding.workspace_id or claim.scope_id != binding.scope_id:
                raise ValueError("postcondition authoritative claim workspace/scope does not match binding")
            if claim.subject_id != binding.subject_id:
                raise ValueError("postcondition authoritative claim subject does not match binding")
            if claim.state_namespace not in targets:
                raise ValueError("postcondition authoritative claim namespace is not a transition target")
            if claim.external_revision_id != binding.external_revision_id:
                raise ValueError("postcondition authoritative claim external revision does not match binding")
            if binding.problem_revision_id and claim.problem_revision_id != binding.problem_revision_id:
                raise ValueError("postcondition authoritative claim problem revision does not match binding")
            correlated_source_ids = set(claim.source_claim_ids).intersection(observed_by_claim_id)
            if not correlated_source_ids:
                raise ValueError(
                    "postcondition authoritative claim must derive from OBSERVED claim correlated through supplied MachineStateObservation"
                )
            if claim.state_namespace in achieved:
                raise ValueError(f"multiple authoritative achieved claims for namespace {claim.state_namespace}")
            achieved[claim.state_namespace] = (claim, row)
            lineage.add(str(row["evidence_id"]))
            for source_claim_id in correlated_source_ids:
                lineage.add(str(observed_by_claim_id[source_claim_id][2]["evidence_id"]))

        if set(achieved) != set(targets):
            missing = sorted(set(targets) - set(achieved))
            extra = sorted(set(achieved) - set(targets))
            raise ValueError(f"postcondition authoritative target coverage mismatch: missing={missing}, extra={extra}")

        comparisons: dict[str, Any] = {}
        all_match = True
        for namespace in sorted(targets):
            target_claim = targets[namespace][0]
            achieved_claim = achieved[namespace][0]
            match = _canonical_value(target_claim.value) == _canonical_value(achieved_claim.value)
            all_match = all_match and match
            comparisons[namespace] = {
                "target_claim_id": target_claim.claim_id,
                "target_fingerprint": target_claim.fingerprint,
                "target_value": deepcopy(target_claim.value),
                "achieved_claim_id": achieved_claim.claim_id,
                "achieved_fingerprint": achieved_claim.fingerprint,
                "achieved_value": deepcopy(achieved_claim.value),
                "comparison": "EXACT_CANONICAL_VALUE_EQUALITY",
                "match": bool(match),
            }

        item = MachinePostconditionVerification(
            transition_id=transition.transition_id,
            effect_id=transition.effect_id,
            binding_id=transition.binding_id,
            verifier_principal_id=verifier_principal_id,
            verdict="VERIFIED" if all_match else "MISMATCH",
            target_state_claim_ids=transition.target_state_claim_ids,
            achieved_state_claim_ids=tuple(claim.claim_id for claim, _ in achieved.values()),
            machine_observation_ids=tuple(machine_observation_ids),
            comparison={"namespaces": comparisons, "all_match": bool(all_match)},
            metadata={
                "effect_status_at_verification": effect.status,
                "effect_execution_id": effect.execution_id or "",
                **deepcopy(dict(metadata or {})),
            },
        )
        projection = self._require_valid_machine_postcondition_projection()
        prior = projection["verifications"].get(item.verification_id)
        if prior is not None:
            if prior["verification"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"machine postcondition verification identity collision: {item.verification_id}")
            return {
                **deepcopy(prior),
                "already_verified": True,
                "effect_status_unchanged": effect.status,
                "state_claim_created": False,
                "fact_authority_created": False,
                "machine_state_mutated": False,
            }

        evidence_id = self._record_machine_postcondition_verification(
            item,
            derived_from=tuple(sorted(lineage)),
            reason=reason,
        )
        return {
            "verification": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_verified": False,
            "effect_status_unchanged": effect.status,
            "state_claim_created": False,
            "fact_authority_created": False,
            "machine_state_mutated": False,
            "effect_authority_granted": False,
        }

    def machine_postcondition_verification_report(self, verification_id: str) -> dict[str, Any]:
        projection = self._require_valid_machine_postcondition_projection()
        try:
            return deepcopy(projection["verifications"][verification_id])
        except KeyError:
            raise KeyError(f"unknown machine postcondition verification: {verification_id}") from None

    def machine_postconditions_report(self) -> dict[str, Any]:
        projection = self._require_valid_machine_postcondition_projection()
        return {
            "runtime_contract": machine_postcondition_runtime_contract(),
            "valid": True,
            "verifications": deepcopy(projection["verifications"]),
            "effect_status_mutation": "NONE",
            "state_claim_creation": "NONE",
            "fact_authority_creation": "NONE",
            "machine_state_mutation": "NONE",
            "parallel_truth_table": "NONE",
            "parallel_effect_lifecycle": "NONE",
        }


__all__ = [
    "MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID",
    "MACHINE_POSTCONDITION_RUNTIME_CONTRACT_VERSION",
    "MACHINE_POSTCONDITION_RUNTIME_STABILITY",
    "MACHINE_POSTCONDITION_CAPABILITIES",
    "MachinePostconditionRuntimeMixin",
    "project_machine_postcondition_evidence",
    "machine_postcondition_runtime_contract",
]
