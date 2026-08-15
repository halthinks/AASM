from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_outcome_v2 import SolverOutcomeV2
from .solver_provenance import SOLVER_EXECUTION_PROFILE_CONTRACT_ID, SolverExecutionProfile
from .solver_provenance_v2 import (
    SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID,
    SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID,
    SolverProfileEvaluationV2,
    SolverRuntimeProvenanceV2,
    build_solver_runtime_provenance_v2,
    evaluate_solver_execution_profile_v2,
    solver_provenance_v2_contract,
)


SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_ID = "aasm.solver.runtime-provenance-v2.runtime.v1"
SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOLVER_PROVENANCE_V2_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_PROVENANCE_RECORD_TYPE = "aasm_solver_provenance_v2_record_type"
_PROVENANCE_DOCUMENT = "document"


def solver_provenance_v2_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_PROVENANCE_V2_RUNTIME_STABILITY,
        "provenance_contract": solver_provenance_v2_contract(),
        "profile_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "provenance_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "evaluation_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "source_result": "EXACT_DURABLE_OPTIMIZATION_RESULT_REQUIRED",
        "source_outcome": "EXACT_DURABLE_SOLVER_OUTCOME_V2_REQUIRED",
        "parallel_provenance_table": "NONE",
        "profile_grants_authority": False,
        "provenance_grants_reproducibility": False,
        "truth_authority": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_PROVENANCE_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("solver provenance v2 Evidence is missing canonical document")


def project_solver_provenance_v2_evidence(records) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {}
    provenances: dict[str, dict[str, Any]] = {}
    evaluations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_PROVENANCE_RECORD_TYPE)
        if record_type not in {"PROFILE", "PROVENANCE_V2", "PROFILE_EVALUATION_V2"}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == "PROFILE":
                item = SolverExecutionProfile.from_dict(document)
                object_id, fingerprint = item.profile_id, item.fingerprint
                target = profiles
                payload_key = "profile"
            elif record_type == "PROVENANCE_V2":
                item = SolverRuntimeProvenanceV2.from_dict(document)
                object_id, fingerprint = item.provenance_id, item.fingerprint
                target = provenances
                payload_key = "provenance"
            else:
                item = SolverProfileEvaluationV2(**{
                    **{key: value for key, value in document.items() if key not in {"fingerprint"}},
                    "deviations": tuple(document.get("deviations") or ()),
                })
                object_id, fingerprint = item.evaluation_id, item.fingerprint
                target = evaluations
                payload_key = "evaluation"
            if metadata.get("object_id") != object_id:
                raise ValueError(f"solver provenance metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"solver provenance metadata fingerprint mismatch: {object_id}")
            candidate = {payload_key: item.to_dict(), "evidence_id": evidence_id}
            prior = target.get(object_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"solver provenance identity collision: {object_id}")
            target[object_id] = candidate
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return {
        "runtime_contract": solver_provenance_v2_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "profiles": profiles,
        "provenances": provenances,
        "evaluations": evaluations,
    }


class SolverProvenanceV2RuntimeMixin:
    def solver_provenance_v2_runtime_contract_report(self) -> dict[str, Any]:
        return solver_provenance_v2_runtime_contract()

    def _solver_provenance_v2_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_solver_provenance_v2_evidence(records)

    def _require_valid_solver_provenance_v2_projection(self) -> dict[str, Any]:
        report = self._solver_provenance_v2_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable solver provenance v2 projection: {report['issues']}")
        return report

    def _record_solver_provenance_document(
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
        evidence_id = f"solver-provenance-v2-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_PROVENANCE_RECORD_TYPE) != record_type or metadata.get(_PROVENANCE_DOCUMENT) != payload:
                raise ValueError(f"solver provenance v2 Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="solver_provenance_v2",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _PROVENANCE_RECORD_TYPE: record_type,
                _PROVENANCE_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def register_solver_execution_profile(
        self,
        profile: SolverExecutionProfile | Mapping[str, Any],
        *,
        evidence_ids: Sequence[str] = (),
        reason: str = "solver execution profile registered",
    ) -> dict[str, Any]:
        item = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
        projection = self._require_valid_solver_provenance_v2_projection()
        prior = projection["profiles"].get(item.profile_id)
        if prior is not None:
            if prior["profile"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"solver execution profile identity collision: {item.profile_id}")
            return {**deepcopy(prior), "already_registered": True}
        evidence_id = self._record_solver_provenance_document(
            record_type="PROFILE",
            object_id=item.profile_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
            derived_from=tuple(evidence_ids),
            reason=reason,
        )
        return {"profile": item.to_dict(), "evidence_id": evidence_id, "already_registered": False}

    def record_solver_runtime_provenance_v2(
        self,
        result_id: str,
        outcome_id: str,
        profile_id: str,
        *,
        execution_id: str,
        adapter_id: str,
        adapter_version: str,
        effective_options: Mapping[str, Any],
        environment_fingerprint: str,
        build_fingerprint: str = "",
        provider_status_map_id: str = "",
        provider_status_map_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
        reason: str = "solver runtime provenance v2 recorded",
    ) -> dict[str, Any]:
        source, source_evidence_id = self._durable_optimization_result(result_id)
        outcome_row = self.solver_outcome_v2_report(outcome_id)
        outcome = SolverOutcomeV2.from_dict(outcome_row["outcome"])
        if outcome.source_result_id != source.result_id or outcome.source_result_fingerprint != source.fingerprint:
            raise ValueError("solver runtime provenance source outcome does not bind exact source result")
        projection = self._require_valid_solver_provenance_v2_projection()
        try:
            profile_row = projection["profiles"][profile_id]
        except KeyError:
            raise KeyError(f"unknown durable solver execution profile: {profile_id}") from None
        profile = SolverExecutionProfile.from_dict(profile_row["profile"])
        provenance = build_solver_runtime_provenance_v2(
            source,
            outcome,
            profile,
            execution_id=execution_id,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            effective_options=effective_options,
            environment_fingerprint=environment_fingerprint,
            build_fingerprint=build_fingerprint,
            provider_status_map_id=provider_status_map_id,
            provider_status_map_fingerprint=provider_status_map_fingerprint,
            dependency_fingerprints=dependency_fingerprints,
            metadata=metadata,
        )
        prior = projection["provenances"].get(provenance.provenance_id)
        if prior is not None:
            if prior["provenance"]["fingerprint"] != provenance.fingerprint:
                raise ValueError(f"solver runtime provenance identity collision: {provenance.provenance_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((
            source_evidence_id,
            str(outcome_row["evidence_id"]),
            str(profile_row["evidence_id"]),
            *map(str, evidence_ids),
        ))))
        evidence_id = self._record_solver_provenance_document(
            record_type="PROVENANCE_V2",
            object_id=provenance.provenance_id,
            object_fingerprint=provenance.fingerprint,
            document=provenance.to_dict(),
            source=SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"provenance": provenance.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def evaluate_solver_runtime_profile_v2(
        self,
        provenance_id: str,
        *,
        evidence_ids: Sequence[str] = (),
        reason: str = "solver runtime profile v2 evaluated",
    ) -> dict[str, Any]:
        projection = self._require_valid_solver_provenance_v2_projection()
        try:
            provenance_row = projection["provenances"][provenance_id]
        except KeyError:
            raise KeyError(provenance_id) from None
        provenance = SolverRuntimeProvenanceV2.from_dict(provenance_row["provenance"])
        try:
            profile_row = projection["profiles"][provenance.profile_id]
        except KeyError:
            raise RuntimeError("durable solver provenance references missing execution profile") from None
        profile = SolverExecutionProfile.from_dict(profile_row["profile"])
        evaluation = evaluate_solver_execution_profile_v2(profile, provenance)
        prior = projection["evaluations"].get(evaluation.evaluation_id)
        if prior is not None:
            if prior["evaluation"]["fingerprint"] != evaluation.fingerprint:
                raise ValueError(f"solver profile evaluation identity collision: {evaluation.evaluation_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((
            str(provenance_row["evidence_id"]),
            str(profile_row["evidence_id"]),
            *map(str, evidence_ids),
        ))))
        evidence_id = self._record_solver_provenance_document(
            record_type="PROFILE_EVALUATION_V2",
            object_id=evaluation.evaluation_id,
            object_fingerprint=evaluation.fingerprint,
            document=evaluation.to_dict(),
            source=SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"evaluation": evaluation.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def solver_provenance_v2_report(self) -> dict[str, Any]:
        return self._solver_provenance_v2_projection()


__all__ = [
    "SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_ID",
    "SOLVER_PROVENANCE_V2_RUNTIME_CONTRACT_VERSION",
    "solver_provenance_v2_runtime_contract",
    "project_solver_provenance_v2_evidence",
    "SolverProvenanceV2RuntimeMixin",
]
