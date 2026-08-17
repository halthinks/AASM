from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .calibration import CalibrationCertificate
from .evidence import EvidenceRecord
from .execution_environment import EnvironmentEvidenceBinding
from .external_machine import MachineStateObservation
from .observation_freshness import ObservationFreshnessAssessment
from .observation_fusion import (
    OBSERVATION_FUSION_CONTRACT_ID,
    ObservationFusionRecord,
    observation_fusion_contract,
)
from .observation_lifecycle import (
    OBSERVATION_DISPOSITION_CONTRACT_ID,
    OBSERVATION_LIFECYCLE_CONTRACT_ID,
    ObservationDisposition,
    ObservationLifecycleRecord,
    ObservationSourceRef,
    observation_lifecycle_contract,
    portable_observation_value,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


OBSERVATION_PROCESSING_RUNTIME_CONTRACT_ID = "aasm.observation.processing.runtime.v1"
OBSERVATION_PROCESSING_RUNTIME_CONTRACT_VERSION = "0.1.0"
OBSERVATION_PROCESSING_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

OBSERVATION_PROCESSING_CAPABILITIES = {
    "record_lifecycle": "observation.lifecycle.record",
    "record_fusion": "observation.fusion.record",
    "record_disposition": "observation.disposition.record",
}

_OBSERVATION_PROCESSING_RECORD_TYPE = "aasm_observation_processing_record_type"
_OBSERVATION_PROCESSING_DOCUMENT = "document"
_LIFECYCLE_RECORD = "OBSERVATION_LIFECYCLE_RECORD"
_FUSION_RECORD = "OBSERVATION_FUSION_RECORD"
_DISPOSITION_RECORD = "OBSERVATION_DISPOSITION"

_ALLOWED_LIFECYCLE_PREDECESSORS = {
    "RAW": {"MACHINE_STATE_OBSERVATION"},
    "NORMALIZED": {"RAW"},
    "CALIBRATED": {"NORMALIZED"},
    "DERIVED": {"NORMALIZED", "CALIBRATED", "DERIVED"},
    "VALIDATED": {"NORMALIZED", "CALIBRATED", "DERIVED", "FUSION_RECORD"},
}
_ALLOWED_FUSION_LIFECYCLE_STAGES = {"NORMALIZED", "CALIBRATED", "DERIVED", "VALIDATED"}


def observation_processing_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": OBSERVATION_PROCESSING_RUNTIME_CONTRACT_ID,
        "contract_version": OBSERVATION_PROCESSING_RUNTIME_CONTRACT_VERSION,
        "stability": OBSERVATION_PROCESSING_RUNTIME_STABILITY,
        "lifecycle_contract": observation_lifecycle_contract(),
        "fusion_contract": observation_fusion_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORDING_NOT_OBSERVATION_TRUTH",
        "capabilities": deepcopy(OBSERVATION_PROCESSING_CAPABILITIES),
        "empirical_root": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY",
        "lifecycle_stage_predecessors": {key: sorted(value) for key, value in _ALLOWED_LIFECYCLE_PREDECESSORS.items()},
        "fusion_lifecycle_inputs": sorted(_ALLOWED_FUSION_LIFECYCLE_STAGES),
        "disposed_source_reuse": "FAIL_CLOSED_FOR_NEW_LIFECYCLE_OR_FUSION_RECORDS",
        "calibrated_stage": "EXACT_ACTIVE_CALIBRATION_AT_EXPLICIT_FRESHNESS_OR_ENVIRONMENT_REFERENCE_TIME",
        "fusion_computation": "CALLER_OR_EXTERNAL_PROCESSOR_SUPPLIES_VALUE_AASM_RECORDS_LINEAGE_ONLY",
        "fusion_agreement_authority": "NONE",
        "validated_stage_authority": "NONE_LOCAL_PROCESSING_LABEL_ONLY",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "source_trust_creation": "NONE",
        "state_claim_creation": "NONE",
        "machine_state_mutation": "NONE",
        "source_observation_mutation": "NONE",
        "current_observation_pointer": "NONE",
        "parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_OBSERVATION_PROCESSING_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("observation-processing Evidence is missing canonical document")


def project_observation_processing_evidence(records) -> dict[str, Any]:
    lifecycle_records: dict[str, dict[str, Any]] = {}
    fusion_records: dict[str, dict[str, Any]] = {}
    dispositions: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_OBSERVATION_PROCESSING_RECORD_TYPE)
        if record_type not in {_LIFECYCLE_RECORD, _FUSION_RECORD, _DISPOSITION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _LIFECYCLE_RECORD:
                item = ObservationLifecycleRecord.from_dict(document)
                object_id, fingerprint = item.record_id, item.fingerprint
                candidate = {"record": item.to_dict(), "evidence_id": evidence_id}
                prior = lifecycle_records.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"observation lifecycle identity collision: {object_id}")
                lifecycle_records[object_id] = candidate
            elif record_type == _FUSION_RECORD:
                item = ObservationFusionRecord.from_dict(document)
                object_id, fingerprint = item.fusion_id, item.fingerprint
                candidate = {"fusion": item.to_dict(), "evidence_id": evidence_id}
                prior = fusion_records.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"observation fusion identity collision: {object_id}")
                fusion_records[object_id] = candidate
            else:
                item = ObservationDisposition.from_dict(document)
                object_id, fingerprint = item.disposition_id, item.fingerprint
                candidate = {"disposition": item.to_dict(), "evidence_id": evidence_id}
                prior = dispositions.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"observation disposition identity collision: {object_id}")
                dispositions[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"observation-processing metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"observation-processing metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })

    def resolve(ref: ObservationSourceRef) -> tuple[str, str] | None:
        if ref.source_kind == "LIFECYCLE_RECORD":
            row = lifecycle_records.get(ref.source_id)
            if row is None:
                return None
            return row["record"]["fingerprint"], row["evidence_id"]
        if ref.source_kind == "FUSION_RECORD":
            row = fusion_records.get(ref.source_id)
            if row is None:
                return None
            return row["fusion"]["fingerprint"], row["evidence_id"]
        return None

    graph: dict[str, list[str]] = {}
    for record_id, row in lifecycle_records.items():
        item = ObservationLifecycleRecord.from_dict(row["record"])
        node = f"LIFECYCLE_RECORD:{record_id}"
        graph[node] = []
        for ref in item.source_refs:
            if ref.source_kind == "MACHINE_STATE_OBSERVATION":
                continue
            target = resolve(ref)
            if target is None:
                issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _LIFECYCLE_RECORD, "error": f"ValueError: unknown lifecycle source {ref.source_kind}:{ref.source_id}"})
                continue
            if target[0] != ref.source_fingerprint:
                issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _LIFECYCLE_RECORD, "error": f"ValueError: lifecycle source fingerprint mismatch {ref.source_kind}:{ref.source_id}"})
            graph[node].append(f"{ref.source_kind}:{ref.source_id}")
    for fusion_id, row in fusion_records.items():
        item = ObservationFusionRecord.from_dict(row["fusion"])
        node = f"FUSION_RECORD:{fusion_id}"
        graph[node] = []
        for ref in item.source_refs:
            target = resolve(ref)
            if target is None:
                issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _FUSION_RECORD, "error": f"ValueError: unknown fusion source {ref.source_kind}:{ref.source_id}"})
                continue
            if target[0] != ref.source_fingerprint:
                issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _FUSION_RECORD, "error": f"ValueError: fusion source fingerprint mismatch {ref.source_kind}:{ref.source_id}"})
            graph[node].append(f"{ref.source_kind}:{ref.source_id}")

    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"observation-processing lineage cycle: {node}")
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, []):
            visit(child)
        visiting.remove(node)
        visited.add(node)
    try:
        for node in sorted(graph):
            visit(node)
    except Exception as exc:
        issues.append({"index": -1, "evidence_id": "", "record_type": "LINEAGE", "error": f"{type(exc).__name__}: {exc}"})

    for disposition_id, row in dispositions.items():
        item = ObservationDisposition.from_dict(row["disposition"])
        target = lifecycle_records.get(item.target_id) if item.target_kind == "LIFECYCLE_RECORD" else fusion_records.get(item.target_id)
        if target is None:
            issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _DISPOSITION_RECORD, "error": f"ValueError: disposition references unknown target: {disposition_id}"})
            continue
        document = target["record"] if item.target_kind == "LIFECYCLE_RECORD" else target["fusion"]
        if document["fingerprint"] != item.target_fingerprint:
            issues.append({"index": -1, "evidence_id": row["evidence_id"], "record_type": _DISPOSITION_RECORD, "error": f"ValueError: disposition target fingerprint mismatch: {disposition_id}"})

    return {
        "runtime_contract": observation_processing_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "lifecycle_records": lifecycle_records,
        "fusion_records": fusion_records,
        "dispositions": dispositions,
    }


class ObservationProcessingRuntimeMixin:
    def observation_processing_contract_report(self) -> dict[str, Any]:
        return observation_processing_runtime_contract()

    def observation_lifecycle_contract_report(self) -> dict[str, Any]:
        return observation_lifecycle_contract()

    def observation_fusion_contract_report(self) -> dict[str, Any]:
        return observation_fusion_contract()

    def _observation_processing_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_observation_processing_evidence(records)

    def _require_valid_observation_processing_projection(self) -> dict[str, Any]:
        report = self._observation_processing_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable observation-processing projection: {report['issues']}")
        return report

    def _authorize_observation_processing_action(
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
            raise PermissionError("observation-processing mutation requires actor_principal_id")
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
            reason=f"observation-processing scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"observation-processing denied {capability}: {result['decision']['reason']}")
        return result

    def _record_observation_processing_document(
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
        evidence_id = f"observation-processing-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_OBSERVATION_PROCESSING_RECORD_TYPE) != record_type
                or metadata.get(_OBSERVATION_PROCESSING_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"observation-processing Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="observation_processing",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _OBSERVATION_PROCESSING_RECORD_TYPE: record_type,
                _OBSERVATION_PROCESSING_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "source_trust_creation": "NONE",
                "state_claim_creation": "NONE",
                "machine_state_mutation": "NONE",
                "source_observation_mutation": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def _active_observation_dispositions(self, projection: Mapping[str, Any], target_kind: str, target_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for row in projection["dispositions"].values():
            document = row["disposition"]
            if document["target_kind"] == target_kind and document["target_id"] == target_id:
                result.append(deepcopy(row))
        return sorted(result, key=lambda row: row["disposition"]["disposition_id"])

    def _resolve_observation_source(self, projection: Mapping[str, Any], ref: ObservationSourceRef) -> dict[str, Any]:
        if ref.source_kind == "MACHINE_STATE_OBSERVATION":
            row = self.machine_state_observation_report(ref.source_id)
            observation = MachineStateObservation.from_dict(row["observation"])
            if observation.fingerprint != ref.source_fingerprint:
                raise ValueError(f"machine observation source fingerprint mismatch: {ref.source_id}")
            state_row = self.state_claim_report(observation.state_claim_id)
            claim = StateClaim.from_dict(state_row["claim"])
            return {
                "source_kind": ref.source_kind,
                "source_id": observation.observation_id,
                "fingerprint": observation.fingerprint,
                "evidence_id": row["evidence_id"],
                "additional_evidence_ids": [state_row["evidence_id"]],
                "workspace_id": claim.workspace_id,
                "scope_id": claim.scope_id,
                "subject_id": claim.subject_id,
                "state_namespace": claim.state_namespace,
                "problem_revision_id": claim.problem_revision_id,
                "external_revision_id": claim.external_revision_id,
                "value": portable_observation_value(claim.value),
                "stage": "MACHINE_STATE_OBSERVATION",
                "document": observation.to_dict(),
                "disposed": [],
            }
        if ref.source_kind == "LIFECYCLE_RECORD":
            try:
                row = projection["lifecycle_records"][ref.source_id]
            except KeyError:
                raise KeyError(f"unknown observation lifecycle source: {ref.source_id}") from None
            item = ObservationLifecycleRecord.from_dict(row["record"])
            if item.fingerprint != ref.source_fingerprint:
                raise ValueError(f"observation lifecycle source fingerprint mismatch: {ref.source_id}")
            disposed = self._active_observation_dispositions(projection, "LIFECYCLE_RECORD", item.record_id)
            return {
                "source_kind": ref.source_kind,
                "source_id": item.record_id,
                "fingerprint": item.fingerprint,
                "evidence_id": row["evidence_id"],
                "additional_evidence_ids": [],
                "workspace_id": item.workspace_id,
                "scope_id": item.scope_id,
                "subject_id": item.subject_id,
                "state_namespace": item.state_namespace,
                "problem_revision_id": item.problem_revision_id,
                "external_revision_id": item.external_revision_id,
                "value": portable_observation_value(item.value),
                "stage": item.stage,
                "document": item.to_dict(),
                "disposed": disposed,
            }
        try:
            row = projection["fusion_records"][ref.source_id]
        except KeyError:
            raise KeyError(f"unknown observation fusion source: {ref.source_id}") from None
        item = ObservationFusionRecord.from_dict(row["fusion"])
        if item.fingerprint != ref.source_fingerprint:
            raise ValueError(f"observation fusion source fingerprint mismatch: {ref.source_id}")
        disposed = self._active_observation_dispositions(projection, "FUSION_RECORD", item.fusion_id)
        return {
            "source_kind": ref.source_kind,
            "source_id": item.fusion_id,
            "fingerprint": item.fingerprint,
            "evidence_id": row["evidence_id"],
            "additional_evidence_ids": [],
            "workspace_id": item.workspace_id,
            "scope_id": item.scope_id,
            "subject_id": item.subject_id,
            "state_namespace": item.state_namespace,
            "problem_revision_id": item.problem_revision_id,
            "external_revision_id": item.external_revision_id,
            "value": portable_observation_value(item.value),
            "stage": "FUSION_RECORD",
            "document": item.to_dict(),
            "disposed": disposed,
        }

    def _root_machine_observation_ids(self, projection: Mapping[str, Any], ref: ObservationSourceRef, seen: set[tuple[str, str]] | None = None) -> set[str]:
        seen = set() if seen is None else set(seen)
        key = (ref.source_kind, ref.source_id)
        if key in seen:
            raise ValueError(f"observation-processing lineage cycle while resolving roots: {ref.source_kind}:{ref.source_id}")
        seen.add(key)
        if ref.source_kind == "MACHINE_STATE_OBSERVATION":
            return {ref.source_id}
        source = self._resolve_observation_source(projection, ref)
        document = source["document"]
        roots: set[str] = set()
        for child in document.get("source_refs", []):
            roots.update(self._root_machine_observation_ids(projection, ObservationSourceRef.from_dict(child), seen))
        return roots

    def _validate_lifecycle_auxiliary_references(self, item: ObservationLifecycleRecord, projection: Mapping[str, Any]) -> list[str]:
        lineage: list[str] = []
        roots: set[str] = set()
        for ref in item.source_refs:
            roots.update(self._root_machine_observation_ids(projection, ref))
        reference_time_ns: int | None = None
        if item.freshness_assessment_id:
            row = self.observation_freshness_assessment_report(item.freshness_assessment_id)
            assessment = ObservationFreshnessAssessment.from_dict(row["assessment"])
            if assessment.fingerprint != item.freshness_assessment_fingerprint:
                raise ValueError("lifecycle freshness assessment fingerprint mismatch")
            if assessment.observation_id not in roots:
                raise ValueError("lifecycle freshness assessment does not refer to a root machine observation")
            lineage.append(str(row["evidence_id"]))
            reference_time_ns = assessment.reference_time_ns
        if item.environment_binding_id:
            row = self.execution_environment_binding_report(item.environment_binding_id)
            binding = EnvironmentEvidenceBinding.from_dict(row["binding"])
            if binding.fingerprint != item.environment_binding_fingerprint:
                raise ValueError("lifecycle execution environment binding fingerprint mismatch")
            if binding.object_kind != "MACHINE_STATE_OBSERVATION" or binding.object_id not in roots:
                raise ValueError("lifecycle execution environment binding does not refer to a root machine observation")
            lineage.append(str(row["evidence_id"]))
            if reference_time_ns is None:
                reference_time_ns = int(row["environment"]["qualified_at_ns"])
        if item.stage == "CALIBRATED":
            if reference_time_ns is None:
                raise ValueError("CALIBRATED lifecycle record requires explicit freshness or environment time context")
            for calibration_id, expected_fingerprint in sorted(item.calibration_bindings.items()):
                row = self.calibration_report(calibration_id, reference_time_ns=reference_time_ns)
                calibration = CalibrationCertificate.from_dict(row["calibration"])
                if calibration.fingerprint != expected_fingerprint:
                    raise ValueError(f"lifecycle calibration fingerprint mismatch: {calibration_id}")
                if not row["active_at_reference_time"]:
                    raise ValueError(f"lifecycle calibration inactive at explicit reference time: {calibration_id}")
                if calibration.workspace_id != item.workspace_id or calibration.scope_id != item.scope_id:
                    raise ValueError("lifecycle calibration workspace/scope mismatch")
                if calibration.subject_id != item.subject_id or calibration.state_namespace != item.state_namespace:
                    raise ValueError("lifecycle calibration subject/namespace mismatch")
                lineage.append(str(row["evidence_id"]))
        return lineage

    def record_observation_lifecycle(
        self,
        record: ObservationLifecycleRecord | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "observation lifecycle record recorded",
    ) -> dict[str, Any]:
        item = record if isinstance(record, ObservationLifecycleRecord) else ObservationLifecycleRecord.from_dict(record)
        if actor_principal_id != item.processor_principal_id:
            raise PermissionError("observation lifecycle actor must equal processor_principal_id")
        projection = self._require_valid_observation_processing_projection()
        resolved = [self._resolve_observation_source(projection, ref) for ref in item.source_refs]
        if any(source["disposed"] for source in resolved):
            raise ValueError("observation lifecycle cannot consume a disposed lifecycle/fusion source")
        allowed = _ALLOWED_LIFECYCLE_PREDECESSORS[item.stage]
        if len(resolved) != 1:
            raise ValueError("observation lifecycle stages are unary; use observation fusion for multi-source processing")
        source = resolved[0]
        predecessor = "MACHINE_STATE_OBSERVATION" if source["source_kind"] == "MACHINE_STATE_OBSERVATION" else source["stage"]
        if predecessor not in allowed:
            raise ValueError(f"invalid observation lifecycle stage transition: {predecessor} -> {item.stage}")
        if source["workspace_id"] != item.workspace_id or source["scope_id"] != item.scope_id:
            raise ValueError("observation lifecycle source workspace/scope mismatch")
        if item.stage in {"RAW", "NORMALIZED", "CALIBRATED", "VALIDATED"}:
            if source["subject_id"] != item.subject_id or source["state_namespace"] != item.state_namespace:
                raise ValueError("observation lifecycle source subject/namespace mismatch")
        if item.problem_revision_id and source["problem_revision_id"] != item.problem_revision_id:
            raise ValueError("observation lifecycle source problem revision mismatch")
        if item.external_revision_id and source["external_revision_id"] != item.external_revision_id:
            raise ValueError("observation lifecycle source external revision mismatch")
        if item.stage == "RAW" and portable_observation_value(item.value) != portable_observation_value(source["value"]):
            raise ValueError("RAW lifecycle value must equal the exact source state claim portable value")
        auxiliary_lineage = self._validate_lifecycle_auxiliary_references(item, projection)
        prior = projection["lifecycle_records"].get(item.record_id)
        if prior is not None:
            if prior["record"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"observation lifecycle identity collision: {item.record_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage_ids = set(map(str, evidence_ids)) | set(map(str, item.evidence_ids)) | set(auxiliary_lineage)
        lineage_ids.add(str(source["evidence_id"]))
        lineage_ids.update(map(str, source["additional_evidence_ids"]))
        lineage = self._require_evidence_ids(tuple(sorted(lineage_ids)))
        authorization = self._authorize_observation_processing_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=OBSERVATION_PROCESSING_CAPABILITIES["record_lifecycle"],
            at_time=at_time,
            metadata={"record_id": item.record_id, "stage": item.stage, "transformation_id": item.transformation_id},
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_observation_processing_document(
            record_type=_LIFECYCLE_RECORD,
            object_id=item.record_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=OBSERVATION_LIFECYCLE_CONTRACT_ID,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "record": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "observation_authority_elevated": False,
            "universal_admission_granted": False,
            "source_observation_mutated": False,
        }

    def record_observation_fusion(
        self,
        fusion: ObservationFusionRecord | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "observation fusion recorded",
    ) -> dict[str, Any]:
        item = fusion if isinstance(fusion, ObservationFusionRecord) else ObservationFusionRecord.from_dict(fusion)
        if actor_principal_id != item.processor_principal_id:
            raise PermissionError("observation fusion actor must equal processor_principal_id")
        projection = self._require_valid_observation_processing_projection()
        sources = [self._resolve_observation_source(projection, ref) for ref in item.source_refs]
        if any(source["disposed"] for source in sources):
            raise ValueError("observation fusion cannot consume a disposed source")
        for source in sources:
            if source["workspace_id"] != item.workspace_id or source["scope_id"] != item.scope_id:
                raise ValueError("observation fusion source workspace/scope mismatch")
            if source["source_kind"] == "LIFECYCLE_RECORD" and source["stage"] not in _ALLOWED_FUSION_LIFECYCLE_STAGES:
                raise ValueError(f"observation fusion source stage not admitted: {source['stage']}")
            if item.problem_revision_id and source["problem_revision_id"] and source["problem_revision_id"] != item.problem_revision_id:
                raise ValueError("observation fusion source problem revision mismatch")
        prior = projection["fusion_records"].get(item.fusion_id)
        if prior is not None:
            if prior["fusion"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"observation fusion identity collision: {item.fusion_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage_ids = set(map(str, evidence_ids)) | set(map(str, item.evidence_ids)) | set(map(str, item.independence_basis_evidence_ids))
        for source in sources:
            lineage_ids.add(str(source["evidence_id"]))
            lineage_ids.update(map(str, source["additional_evidence_ids"]))
        lineage = self._require_evidence_ids(tuple(sorted(lineage_ids)))
        authorization = self._authorize_observation_processing_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=OBSERVATION_PROCESSING_CAPABILITIES["record_fusion"],
            at_time=at_time,
            metadata={"fusion_id": item.fusion_id, "fusion_method_id": item.fusion_method_id, "source_count": len(item.source_refs)},
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_observation_processing_document(
            record_type=_FUSION_RECORD,
            object_id=item.fusion_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=OBSERVATION_FUSION_CONTRACT_ID,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "fusion": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "observation_authority_elevated": False,
            "agreement_granted_authority": False,
            "declared_independence_granted_authority": False,
            "source_observation_mutated": False,
        }

    def record_observation_disposition(
        self,
        disposition: ObservationDisposition | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "observation disposition recorded",
    ) -> dict[str, Any]:
        item = disposition if isinstance(disposition, ObservationDisposition) else ObservationDisposition.from_dict(disposition)
        if actor_principal_id != item.actor_principal_id:
            raise PermissionError("observation disposition actor must equal actor_principal_id")
        projection = self._require_valid_observation_processing_projection()
        if item.target_kind == "LIFECYCLE_RECORD":
            target = projection["lifecycle_records"].get(item.target_id)
            document_key = "record"
        else:
            target = projection["fusion_records"].get(item.target_id)
            document_key = "fusion"
        if target is None:
            raise KeyError(f"unknown observation disposition target: {item.target_kind}:{item.target_id}")
        if target[document_key]["fingerprint"] != item.target_fingerprint:
            raise ValueError("observation disposition target fingerprint mismatch")
        prior = projection["dispositions"].get(item.disposition_id)
        if prior is not None:
            if prior["disposition"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"observation disposition identity collision: {item.disposition_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage_ids = set(map(str, evidence_ids)) | set(map(str, item.evidence_ids)) | {str(target["evidence_id"])}
        lineage = self._require_evidence_ids(tuple(sorted(lineage_ids)))
        authorization = self._authorize_observation_processing_action(
            actor_principal_id=actor_principal_id,
            workspace_id=str(target[document_key]["workspace_id"]),
            scope_id=str(target[document_key]["scope_id"]),
            capability=OBSERVATION_PROCESSING_CAPABILITIES["record_disposition"],
            at_time=at_time,
            metadata={"disposition_id": item.disposition_id, "target_kind": item.target_kind, "target_id": item.target_id, "disposition": item.disposition},
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_observation_processing_document(
            record_type=_DISPOSITION_RECORD,
            object_id=item.disposition_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=OBSERVATION_DISPOSITION_CONTRACT_ID,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "disposition": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "source_deleted": False,
            "source_mutated": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
        }

    def observation_lifecycle_record_report(self, record_id: str) -> dict[str, Any]:
        projection = self._require_valid_observation_processing_projection()
        try:
            row = deepcopy(projection["lifecycle_records"][str(record_id)])
        except KeyError:
            raise KeyError(f"unknown observation lifecycle record: {record_id}") from None
        row["dispositions"] = self._active_observation_dispositions(projection, "LIFECYCLE_RECORD", str(record_id))
        return row

    def observation_fusion_record_report(self, fusion_id: str) -> dict[str, Any]:
        projection = self._require_valid_observation_processing_projection()
        try:
            row = deepcopy(projection["fusion_records"][str(fusion_id)])
        except KeyError:
            raise KeyError(f"unknown observation fusion record: {fusion_id}") from None
        row["dispositions"] = self._active_observation_dispositions(projection, "FUSION_RECORD", str(fusion_id))
        return row

    def observation_disposition_report(self, disposition_id: str) -> dict[str, Any]:
        projection = self._require_valid_observation_processing_projection()
        try:
            return deepcopy(projection["dispositions"][str(disposition_id)])
        except KeyError:
            raise KeyError(f"unknown observation disposition: {disposition_id}") from None

    def observation_processing_report(self, *, workspace_id: str | None = None, scope_id: str | None = None) -> dict[str, Any]:
        projection = self._require_valid_observation_processing_projection()
        lifecycle_records = {
            key: deepcopy(row)
            for key, row in sorted(projection["lifecycle_records"].items())
            if (workspace_id is None or row["record"]["workspace_id"] == workspace_id)
            and (scope_id is None or row["record"]["scope_id"] == scope_id)
        }
        fusion_records = {
            key: deepcopy(row)
            for key, row in sorted(projection["fusion_records"].items())
            if (workspace_id is None or row["fusion"]["workspace_id"] == workspace_id)
            and (scope_id is None or row["fusion"]["scope_id"] == scope_id)
        }
        target_ids = set(lifecycle_records) | set(fusion_records)
        dispositions = {
            key: deepcopy(row)
            for key, row in sorted(projection["dispositions"].items())
            if row["disposition"]["target_id"] in target_ids
        }
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "valid": True,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "lifecycle_records": lifecycle_records,
            "fusion_records": fusion_records,
            "dispositions": dispositions,
            "fact_authority_creation": "NONE",
            "effect_authority": "NONE",
            "observation_authority_elevation": "NONE",
            "current_observation_pointer": "NONE",
            "parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY",
            "parallel_truth_table": "NONE",
        }


__all__ = [
    "OBSERVATION_PROCESSING_RUNTIME_CONTRACT_ID",
    "OBSERVATION_PROCESSING_RUNTIME_CONTRACT_VERSION",
    "OBSERVATION_PROCESSING_RUNTIME_STABILITY",
    "OBSERVATION_PROCESSING_CAPABILITIES",
    "ObservationProcessingRuntimeMixin",
    "project_observation_processing_evidence",
    "observation_processing_runtime_contract",
]
