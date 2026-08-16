from __future__ import annotations

from copy import deepcopy
import json
from math import isfinite
from typing import Any, Mapping, Sequence

from .effect_capability import EffectCapability
from .effects import EffectIntent, EffectStatus
from .evidence import EvidenceRecord
from .external_machine_transition import MACHINE_TRANSITION_CONTRACT_ID
from .physical_authority import AuthorityDomain, AuthorityLease
from .physical_effect_binding import (
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
    PhysicalEffectAuthorityBinding,
    physical_effect_authority_binding_contract,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID = "aasm.effect.physical-authority-integration.runtime.v1"
PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION = "0.1.0"
PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES = {"bind": "physical.effect.bind"}

_PHYSICAL_EFFECT_RECORD_TYPE = "aasm_physical_effect_integration_record_type"
_PHYSICAL_EFFECT_DOCUMENT = "document"
_PHYSICAL_EFFECT_BINDING_RECORD = "PHYSICAL_EFFECT_AUTHORITY_BINDING"
_PHYSICAL_EFFECT_RECHECK_RECORD = "PHYSICAL_EFFECT_AUTHORITY_RECHECK"


def physical_effect_integration_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
        "contract_version": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION,
        "stability": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY,
        "semantic_contract": physical_effect_authority_binding_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "binding_authority": "EXISTING_AASM_SCOPED_AUTHORITY_PHYSICAL_EFFECT_BIND",
        "effect_authority": "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED",
        "authorization_boundary": "LIVE_PHYSICAL_AUTHORITY_RECHECK_THEN_EXISTING_AUTHORIZE_EFFECT",
        "execution_boundary": "LIVE_PHYSICAL_AUTHORITY_RECHECK_THEN_EXISTING_EXECUTE_EFFECT",
        "machine_transition_binding": "MANDATORY_BEFORE_AUTHORIZATION_OR_NEW_DISPATCH",
        "ordinary_unbound_effect_compatibility": "PRESERVED",
        "prior_use_validation": "EVIDENCE_ONLY_NEVER_REUSABLE_AUTHORIZATION",
        "operation_source": "DURABLE_EFFECT_SPEC_PAYLOAD_OPERATION_OR_EFFECT_TYPE",
        "numeric_parameter_source": "DURABLE_EFFECT_COMMAND_PAYLOAD_RECURSIVE_FINITE_NUMERIC_LEAVES",
        "numeric_bounds": "EXACT_PARAMETER_NAME_SET_AND_INTERVAL_CONTAINMENT",
        "point_of_use_recheck": "LEASE_CAPABILITY_FINGERPRINT_EPOCH_REVOCATION_HOLDER_SCOPE_SUBJECT_REVISION_OPERATION_BOUNDS",
        "task_lease": "EXISTING_V54_TASKLEASE_UNCHANGED",
        "resource_governance": "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED",
        "ownership": "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED",
        "unknown_and_reconciliation": "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_store": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "parallel_dispatcher": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_PHYSICAL_EFFECT_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("physical-effect integration Evidence is missing canonical document")


def project_physical_effect_integration_evidence(records) -> dict[str, Any]:
    bindings: dict[str, dict[str, Any]] = {}
    rechecks: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_PHYSICAL_EFFECT_RECORD_TYPE)
        if record_type not in {_PHYSICAL_EFFECT_BINDING_RECORD, _PHYSICAL_EFFECT_RECHECK_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _PHYSICAL_EFFECT_BINDING_RECORD:
                item = PhysicalEffectAuthorityBinding.from_dict(document)
                object_id = item.effect_id
                fingerprint = item.fingerprint
                candidate = {
                    "binding": item.to_dict(),
                    "evidence_id": evidence_id,
                }
                prior = bindings.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"effect has multiple non-identical physical authority bindings: {object_id}")
                bindings[object_id] = candidate
            else:
                object_id = str(document.get("recheck_id") or "")
                if not object_id:
                    raise ValueError("physical effect recheck_id is required")
                fingerprint = semantic_fingerprint(document)
                candidate = {"recheck": document, "evidence_id": evidence_id}
                prior = rechecks.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"physical effect recheck identity collision: {object_id}")
                rechecks[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"physical-effect metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"physical-effect metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": physical_effect_integration_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "bindings": bindings,
        "rechecks": rechecks,
    }


def _numeric_leaves(value: Any, *, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(value, Mapping):
        for raw_key, child in sorted(value.items(), key=lambda pair: str(pair[0])):
            key = str(raw_key).strip()
            if not key:
                raise ValueError("physical effect command contains an empty parameter key")
            child_prefix = key if not prefix else f"{prefix}.{key}"
            out.update(_numeric_leaves(child, prefix=child_prefix))
        return out
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            out.update(_numeric_leaves(child, prefix=child_prefix))
        return out
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return out
    if isinstance(value, (int, float)):
        if not prefix:
            raise ValueError("physical effect numeric command leaf requires a stable parameter path")
        number = float(value)
        if not isfinite(number):
            raise ValueError(f"physical effect numeric parameter must be finite: {prefix}")
        out[prefix] = number
        return out
    raise TypeError(f"unsupported physical effect command value at {prefix or '<root>'}: {type(value)!r}")


class PhysicalEffectIntegrationRuntimeMixin:
    """PR-3H: make current physical authority mandatory inside the existing Effect lifecycle."""

    def physical_effect_integration_contract_report(self) -> dict[str, Any]:
        return physical_effect_integration_runtime_contract()

    def _physical_effect_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_physical_effect_integration_evidence(records)

    def _require_valid_physical_effect_projection(self) -> dict[str, Any]:
        report = self._physical_effect_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable physical-effect integration projection: {report['issues']}")
        return report

    def _record_physical_effect_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"physical-effect-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_PHYSICAL_EFFECT_RECORD_TYPE) != record_type
                or metadata.get(_PHYSICAL_EFFECT_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"physical-effect Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="physical_effect_integration",
            statement=canonical_semantic_json(payload),
            source=PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _PHYSICAL_EFFECT_RECORD_TYPE: record_type,
                _PHYSICAL_EFFECT_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "authority": "EVIDENCE_ONLY_UNLESS_EXISTING_EFFECT_AUTHORITY_SEPARATELY_PASSES",
                "parallel_effect_lifecycle": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def _authorize_physical_effect_binding_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        effect_id: str,
        at_time: float,
        derived_from: Sequence[str],
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("physical effect binding requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES["bind"],
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata={"effect_id": effect_id},
            ),
            derived_from=tuple(derived_from),
            reason="physical effect binding authority evaluated",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"physical effect binding denied: {result['decision']['reason']}"
            )
        return result

    @staticmethod
    def _effect_operation_and_numeric_parameters(record) -> tuple[str, dict[str, float]]:
        payload = deepcopy(dict(record.spec.payload or {}))
        operation = str(payload.get("operation") or record.spec.effect_type or "").strip()
        if not operation:
            raise ValueError("physical effect has no stable operation identity")
        command = payload.get("command")
        numeric_source = command if isinstance(command, Mapping) else payload
        numeric_parameters = _numeric_leaves(numeric_source)
        return operation, numeric_parameters

    @staticmethod
    def _effect_requires_physical_binding(record, intent: EffectIntent) -> bool:
        metadata = dict(intent.metadata or {})
        return bool(
            record.spec.effect_type == "machine.transition"
            or metadata.get("machine_transition_contract_id") == MACHINE_TRANSITION_CONTRACT_ID
            or metadata.get("physical_authority_required") is True
        )

    def _physical_effect_binding_row(self, effect_id: str) -> dict[str, Any] | None:
        projection = self._require_valid_physical_effect_projection()
        row = projection["bindings"].get(str(effect_id))
        return None if row is None else deepcopy(row)

    def bind_physical_effect_authority(
        self,
        effect_id: str,
        *,
        authority_lease_id: str,
        effect_capability_id: str,
        actor_principal_id: str,
        at_time: float,
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
        reason: str = "physical effect authority bound",
    ) -> dict[str, Any]:
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None:
            raise PermissionError("physical effect binding requires an existing v0.54 EffectIntent")
        if record.status != EffectStatus.PROPOSED.value:
            raise PermissionError("physical effect authority must be bound while effect is PROPOSED")
        intent = EffectIntent.from_dict(record.intent)
        lease_row = self.authority_lease_report(authority_lease_id, at_time=at_time)
        lease = AuthorityLease.from_dict(lease_row["lease"])
        capability_row = self.effect_capability_report(effect_capability_id, at_time=at_time)
        capability = EffectCapability.from_dict(capability_row["capability"])
        domain_row = self.authority_domain_report(capability.domain_id)
        domain = AuthorityDomain.from_dict(domain_row["domain"])

        if capability.authority_lease_id != lease.lease_id or capability.domain_id != lease.domain_id:
            raise ValueError("effect capability does not belong to supplied authority lease")
        if capability.domain_id != domain.domain_id:
            raise ValueError("effect capability does not belong to supplied authority domain")
        if not lease_row["active_at_time"] or not capability_row["active_at_time"]:
            raise PermissionError("physical effect binding requires active lease and capability")
        if actor_principal_id != capability.holder_principal_id or actor_principal_id != lease.holder_principal_id:
            raise PermissionError("physical effect binding actor must be current capability and lease holder")
        if intent.workspace_id != domain.workspace_id or intent.scope_id != domain.scope_id:
            raise PermissionError("physical effect intent crosses authority domain workspace/scope")
        if lease.workspace_id != domain.workspace_id or lease.scope_id != domain.scope_id:
            raise ValueError("authority lease workspace/scope no longer matches domain")
        if capability.workspace_id != domain.workspace_id or capability.scope_id != domain.scope_id:
            raise ValueError("effect capability workspace/scope no longer matches domain")
        if capability.subject_id != domain.subject_id:
            raise ValueError("effect capability subject no longer matches domain")
        if capability.authority_epoch != lease.epoch:
            raise ValueError("effect capability authority epoch no longer matches lease")
        if capability.problem_revision_id != lease.problem_revision_id or capability.problem_revision_id != domain.problem_revision_id:
            raise ValueError("physical effect problem revision mismatch")
        if capability.external_revision_id != lease.external_revision_id or capability.external_revision_id != domain.external_revision_id:
            raise ValueError("physical effect external revision mismatch")

        spec_payload = deepcopy(dict(record.spec.payload or {}))
        if spec_payload.get("subject_id") and str(spec_payload["subject_id"]) != domain.subject_id:
            raise ValueError("physical effect payload subject does not match authority domain")
        if spec_payload.get("external_revision_id") and str(spec_payload["external_revision_id"]) != domain.external_revision_id:
            raise ValueError("physical effect payload external revision does not match authority domain")
        if record.spec.effect_type == "machine.transition" and spec_payload.get("binding_id"):
            machine_binding_row = self.machine_binding_report(str(spec_payload["binding_id"]))
            machine_binding = machine_binding_row["binding"]
            if machine_binding.get("subject_id") != domain.subject_id:
                raise ValueError("machine transition binding subject does not match authority domain")
            if machine_binding.get("external_revision_id") != domain.external_revision_id:
                raise ValueError("machine transition binding external revision does not match authority domain")
            if str(machine_binding.get("problem_revision_id") or "") != domain.problem_revision_id:
                raise ValueError("machine transition binding problem revision does not match authority domain")

        operation, numeric_parameters = self._effect_operation_and_numeric_parameters(record)
        if not capability.allows_operation(operation):
            raise PermissionError("physical effect operation is outside capability allow-list")
        if set(numeric_parameters) != set(capability.numeric_bounds):
            raise PermissionError("physical effect numeric parameter names must exactly match capability bounds")
        if not capability.bounds_allow(numeric_parameters):
            raise PermissionError("physical effect numeric parameters exceed capability bounds")

        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        *map(str, record.evidence),
                        str(domain_row["evidence_id"]),
                        str(lease_row["evidence_id"]),
                        str(capability_row["evidence_id"]),
                    )
                )
            )
        )
        authorization = self._authorize_physical_effect_binding_action(
            actor_principal_id=actor_principal_id,
            workspace_id=intent.workspace_id,
            scope_id=intent.scope_id,
            effect_id=effect_id,
            at_time=at_time,
            derived_from=lineage,
        )
        item = PhysicalEffectAuthorityBinding(
            effect_id=effect_id,
            effect_intent_id=intent.intent_id,
            effect_intent_fingerprint=intent.fingerprint,
            workspace_id=intent.workspace_id,
            scope_id=intent.scope_id,
            subject_id=domain.subject_id,
            authority_domain_id=domain.domain_id,
            authority_domain_fingerprint=domain.fingerprint,
            authority_lease_id=lease.lease_id,
            authority_lease_fingerprint=lease.fingerprint,
            effect_capability_id=capability.capability_id,
            effect_capability_fingerprint=capability.fingerprint,
            holder_principal_id=capability.holder_principal_id,
            authority_epoch=capability.authority_epoch,
            effective_revocation_generation=int(capability_row["effective_revocation_generation"]),
            operation=operation,
            numeric_parameters=numeric_parameters,
            problem_revision_id=domain.problem_revision_id,
            external_revision_id=domain.external_revision_id,
            metadata=deepcopy(dict(metadata or {})),
        )
        projection = self._require_valid_physical_effect_projection()
        prior = projection["bindings"].get(effect_id)
        if prior is not None:
            if prior["binding"]["fingerprint"] != item.fingerprint:
                raise ValueError("effect already has a different physical authority binding")
            return {
                **deepcopy(prior),
                "already_bound": True,
                "effect_authority_granted": False,
            }
        evidence_id = self._record_physical_effect_document(
            record_type=_PHYSICAL_EFFECT_BINDING_RECORD,
            object_id=effect_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            derived_from=tuple(sorted(set((*lineage, str(authorization["evidence_id"]))))),
            reason=reason,
        )
        return {
            "binding": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_bound": False,
            "effect_authority_granted": False,
        }

    def _validate_physical_effect_authority_at_time(
        self,
        effect_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str | None,
        at_time: float,
    ) -> dict[str, Any] | None:
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None:
            return None
        intent = EffectIntent.from_dict(record.intent)
        binding_row = self._physical_effect_binding_row(effect_id)
        required = self._effect_requires_physical_binding(record, intent)
        if binding_row is None:
            if required:
                raise PermissionError("physical/external machine effect requires a physical authority binding before authorization or dispatch")
            return None
        binding = PhysicalEffectAuthorityBinding.from_dict(binding_row["binding"])
        if intent.intent_id != binding.effect_intent_id or intent.fingerprint != binding.effect_intent_fingerprint:
            raise PermissionError("physical effect binding no longer matches durable EffectIntent")
        if workspace_id != binding.workspace_id or scope_id != binding.scope_id:
            raise PermissionError("physical effect authorization crosses binding workspace/scope")
        if not actor_principal_id or actor_principal_id != binding.holder_principal_id:
            raise PermissionError("physical effect authorization/execution actor must equal current capability holder")

        domain_row = self.authority_domain_report(binding.authority_domain_id)
        domain = AuthorityDomain.from_dict(domain_row["domain"])
        lease_row = self.authority_lease_report(binding.authority_lease_id, at_time=at_time)
        lease = AuthorityLease.from_dict(lease_row["lease"])
        capability_row = self.effect_capability_report(binding.effect_capability_id, at_time=at_time)
        capability = EffectCapability.from_dict(capability_row["capability"])

        if domain.fingerprint != binding.authority_domain_fingerprint:
            raise PermissionError("physical effect authority domain fingerprint is stale")
        if lease.fingerprint != binding.authority_lease_fingerprint:
            raise PermissionError("physical effect authority lease fingerprint is stale")
        if capability.fingerprint != binding.effect_capability_fingerprint:
            raise PermissionError("physical effect capability fingerprint is stale")
        if not lease_row["active_at_time"]:
            raise PermissionError("physical effect authority lease is not active at point of use")
        if not capability_row["active_at_time"]:
            raise PermissionError("physical effect capability is not active at point of use")
        if lease.domain_id != binding.authority_domain_id or capability.domain_id != binding.authority_domain_id:
            raise PermissionError("physical effect authority domain identity drift")
        if capability.authority_lease_id != binding.authority_lease_id:
            raise PermissionError("physical effect capability authority lease identity drift")
        if lease.holder_principal_id != binding.holder_principal_id or capability.holder_principal_id != binding.holder_principal_id:
            raise PermissionError("physical effect authority holder drift")
        if lease.epoch != binding.authority_epoch or capability.authority_epoch != binding.authority_epoch:
            raise PermissionError("physical effect authority epoch is stale")
        if int(capability_row["effective_revocation_generation"]) != binding.effective_revocation_generation:
            raise PermissionError("physical effect capability revocation generation is stale")
        if domain.workspace_id != binding.workspace_id or domain.scope_id != binding.scope_id:
            raise PermissionError("physical effect domain scope drift")
        if domain.subject_id != binding.subject_id or capability.subject_id != binding.subject_id:
            raise PermissionError("physical effect subject identity drift")
        if domain.problem_revision_id != binding.problem_revision_id or lease.problem_revision_id != binding.problem_revision_id or capability.problem_revision_id != binding.problem_revision_id:
            raise PermissionError("physical effect problem revision is stale")
        if domain.external_revision_id != binding.external_revision_id or lease.external_revision_id != binding.external_revision_id or capability.external_revision_id != binding.external_revision_id:
            raise PermissionError("physical effect external revision is stale")

        operation, numeric_parameters = self._effect_operation_and_numeric_parameters(record)
        if operation != binding.operation or not capability.allows_operation(operation):
            raise PermissionError("physical effect operation no longer matches bounded capability")
        if numeric_parameters != dict(binding.numeric_parameters):
            raise PermissionError("physical effect numeric parameters no longer match durable authority binding")
        if set(numeric_parameters) != set(capability.numeric_bounds):
            raise PermissionError("physical effect numeric parameter names no longer match capability bounds")
        if not capability.bounds_allow(numeric_parameters):
            raise PermissionError("physical effect numeric parameters exceed capability bounds")

        return {
            "binding": binding.to_dict(),
            "binding_evidence_id": binding_row["evidence_id"],
            "domain_evidence_id": domain_row["evidence_id"],
            "lease_evidence_id": lease_row["evidence_id"],
            "capability_evidence_id": capability_row["evidence_id"],
            "at_time": float(at_time),
        }

    def _record_physical_effect_recheck(
        self,
        effect_id: str,
        *,
        boundary: str,
        validation: Mapping[str, Any],
    ) -> str:
        binding = PhysicalEffectAuthorityBinding.from_dict(validation["binding"])
        document = {
            "contract_id": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
            "contract_version": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION,
            "effect_id": effect_id,
            "binding_id": binding.binding_id,
            "binding_fingerprint": binding.fingerprint,
            "boundary": str(boundary),
            "at_time": float(validation["at_time"]),
            "holder_principal_id": binding.holder_principal_id,
            "authority_epoch": binding.authority_epoch,
            "effective_revocation_generation": binding.effective_revocation_generation,
            "operation": binding.operation,
            "numeric_parameters": deepcopy(dict(binding.numeric_parameters)),
            "validation_only": True,
            "effect_authority_granted": False,
            "reusable_authorization_token": False,
        }
        recheck_id = f"physical-effect-recheck-{semantic_fingerprint(document)[:24]}"
        document["recheck_id"] = recheck_id
        fingerprint = semantic_fingerprint(document)
        return self._record_physical_effect_document(
            record_type=_PHYSICAL_EFFECT_RECHECK_RECORD,
            object_id=recheck_id,
            object_fingerprint=fingerprint,
            document=document,
            derived_from=(
                str(validation["binding_evidence_id"]),
                str(validation["domain_evidence_id"]),
                str(validation["lease_evidence_id"]),
                str(validation["capability_evidence_id"]),
            ),
            reason=f"physical effect authority rechecked at {boundary}",
        )

    def authorize_effect(
        self,
        effect_id,
        authority="controller",
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        if not workspace_id or not scope_id:
            return super().authorize_effect(
                effect_id,
                authority=authority,
                workspace_id=workspace_id,
                scope_id=scope_id,
                actor_principal_id=actor_principal_id,
                at_time=at_time,
            )
        validation = self._validate_physical_effect_authority_at_time(
            effect_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        if validation is not None:
            self._record_physical_effect_recheck(effect_id, boundary="AUTHORIZE", validation=validation)
        return super().authorize_effect(
            effect_id,
            authority=authority,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )

    def execute_effect(
        self,
        effect_id,
        executor,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status != EffectStatus.SUCCEEDED.value and workspace_id and scope_id:
            validation = self._validate_physical_effect_authority_at_time(
                effect_id,
                workspace_id=workspace_id,
                scope_id=scope_id,
                actor_principal_id=actor_principal_id,
                at_time=at_time,
            )
            if validation is not None:
                self._record_physical_effect_recheck(effect_id, boundary="EXECUTE", validation=validation)
        return super().execute_effect(
            effect_id,
            executor,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )

    def physical_effect_binding_report(self, effect_id: str, *, at_time: float = 0.0) -> dict[str, Any]:
        row = self._physical_effect_binding_row(effect_id)
        if row is None:
            raise KeyError(f"effect has no physical authority binding: {effect_id}")
        binding = PhysicalEffectAuthorityBinding.from_dict(row["binding"])
        current = self._validate_physical_effect_authority_at_time(
            effect_id,
            workspace_id=binding.workspace_id,
            scope_id=binding.scope_id,
            actor_principal_id=binding.holder_principal_id,
            at_time=at_time,
        )
        return {**row, "current_validation": current, "effect_authority_granted": False}

    def physical_effect_integration_report(self) -> dict[str, Any]:
        report = self._require_valid_physical_effect_projection()
        return deepcopy(report)


__all__ = [
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY",
    "PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES",
    "project_physical_effect_integration_evidence",
    "physical_effect_integration_runtime_contract",
    "PhysicalEffectIntegrationRuntimeMixin",
]
