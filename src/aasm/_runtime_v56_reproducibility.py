from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .reproducibility import (
    REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID,
    REPRODUCIBILITY_RUN_CONTRACT_ID,
    ReproducibilityCertificate,
    ReproducibilityRun,
    compare_reproducibility_runs,
    reproducibility_contract,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_outcome_v2 import SolverOutcomeV2
from .solver_provenance_v2 import SolverProfileEvaluationV2, SolverRuntimeProvenanceV2


REPRODUCIBILITY_RUNTIME_CONTRACT_ID = "aasm.solver.reproducibility.runtime.v1"
REPRODUCIBILITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
REPRODUCIBILITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_REPRO_RECORD_TYPE = "aasm_solver_reproducibility_record_type"
_REPRO_DOCUMENT = "document"


def reproducibility_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": REPRODUCIBILITY_RUNTIME_CONTRACT_ID,
        "contract_version": REPRODUCIBILITY_RUNTIME_CONTRACT_VERSION,
        "stability": REPRODUCIBILITY_RUNTIME_STABILITY,
        "model_contract": reproducibility_contract(),
        "run_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "certificate_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "run_materialization": "RE_RESOLVE_EXACT_BOUND_RESULT_OUTCOME_PROVENANCE_EVALUATION",
        "parallel_reproducibility_table": "NONE",
        "agreement_grants_truth": False,
        "truth_authority": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_REPRO_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("reproducibility Evidence is missing canonical document")


def _document_fingerprint(document: Mapping[str, Any], identity_key: str) -> str:
    payload = deepcopy(dict(document))
    fingerprint = str(payload.pop("fingerprint", ""))
    expected = semantic_fingerprint(payload)
    if fingerprint != expected:
        raise ValueError(f"reproducibility {identity_key} fingerprint mismatch")
    return fingerprint


def project_reproducibility_evidence(records) -> dict[str, Any]:
    runs: dict[str, dict[str, Any]] = {}
    certificates: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_REPRO_RECORD_TYPE)
        if record_type not in {"RUN", "CERTIFICATE"}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == "RUN":
                object_id = str(document.get("run_id") or "")
                _document_fingerprint(document, "run")
                target, payload_key = runs, "run"
            else:
                object_id = str(document.get("certificate_id") or "")
                _document_fingerprint(document, "certificate")
                target, payload_key = certificates, "certificate"
            if not object_id:
                raise ValueError("reproducibility record lacks object identity")
            if metadata.get("object_id") != object_id:
                raise ValueError("reproducibility metadata object_id mismatch")
            candidate = {payload_key: document, "evidence_id": evidence_id}
            prior = target.get(object_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"reproducibility identity collision: {object_id}")
            target[object_id] = candidate
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return {
        "runtime_contract": reproducibility_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "runs": runs,
        "certificates": certificates,
    }


class ReproducibilityRuntimeMixin:
    def reproducibility_runtime_contract_report(self) -> dict[str, Any]:
        return reproducibility_runtime_contract()

    def _reproducibility_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_reproducibility_evidence(records)

    def _require_valid_reproducibility_projection(self) -> dict[str, Any]:
        report = self._reproducibility_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable reproducibility projection: {report['issues']}")
        return report

    def _record_reproducibility_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        evidence_id = f"reproducibility-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_REPRO_RECORD_TYPE) != record_type or metadata.get(_REPRO_DOCUMENT) != payload:
                raise ValueError(f"reproducibility Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="solver_reproducibility",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _REPRO_RECORD_TYPE: record_type,
                _REPRO_DOCUMENT: payload,
                "object_id": object_id,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    @staticmethod
    def _evaluation_from_document(value: Mapping[str, Any]) -> SolverProfileEvaluationV2:
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload["deviations"] = tuple(payload.get("deviations") or ())
        return SolverProfileEvaluationV2(**payload)

    def _materialize_reproducibility_run(self, document: Mapping[str, Any]) -> ReproducibilityRun:
        result, _ = self._durable_optimization_result(str(document["result_id"]))
        if result.fingerprint != document["result_fingerprint"]:
            raise ValueError("reproducibility run result fingerprint no longer matches durable result")
        outcome_row = self.solver_outcome_v2_report(str(document["outcome_id"]))
        outcome = SolverOutcomeV2.from_dict(outcome_row["outcome"])
        if outcome.fingerprint != document["outcome_fingerprint"]:
            raise ValueError("reproducibility run outcome fingerprint mismatch")
        provenance_projection = self._require_valid_solver_provenance_v2_projection()
        try:
            provenance_row = provenance_projection["provenances"][str(document["provenance_id"])]
            evaluation_row = provenance_projection["evaluations"][str(document["profile_evaluation_id"])]
        except KeyError as exc:
            raise ValueError("reproducibility run references missing durable provenance/evaluation") from exc
        provenance = SolverRuntimeProvenanceV2.from_dict(provenance_row["provenance"])
        evaluation = self._evaluation_from_document(evaluation_row["evaluation"])
        if provenance.fingerprint != document["provenance_fingerprint"]:
            raise ValueError("reproducibility run provenance fingerprint mismatch")
        if evaluation.fingerprint != document["profile_evaluation_fingerprint"]:
            raise ValueError("reproducibility run profile-evaluation fingerprint mismatch")
        run = ReproducibilityRun(
            result,
            outcome,
            provenance,
            evaluation,
            semantic_projection_fingerprint=str(document.get("semantic_projection_fingerprint") or ""),
            proof_fingerprint=str(document.get("proof_fingerprint") or ""),
            artifact_fingerprint=str(document.get("artifact_fingerprint") or ""),
            metadata=deepcopy(document.get("metadata") or {}),
            run_id=str(document["run_id"]),
        )
        if run.fingerprint != document["fingerprint"]:
            raise ValueError("reproducibility run rematerialization fingerprint mismatch")
        return run

    def record_reproducibility_run(
        self,
        result_id: str,
        outcome_id: str,
        provenance_id: str,
        profile_evaluation_id: str,
        *,
        semantic_projection_fingerprint: str = "",
        proof_fingerprint: str = "",
        artifact_fingerprint: str = "",
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
        reason: str = "reproducibility run recorded",
    ) -> dict[str, Any]:
        result, result_evidence_id = self._durable_optimization_result(result_id)
        outcome_row = self.solver_outcome_v2_report(outcome_id)
        outcome = SolverOutcomeV2.from_dict(outcome_row["outcome"])
        provenance_projection = self._require_valid_solver_provenance_v2_projection()
        try:
            provenance_row = provenance_projection["provenances"][provenance_id]
            evaluation_row = provenance_projection["evaluations"][profile_evaluation_id]
        except KeyError as exc:
            raise KeyError("unknown durable provenance or profile evaluation") from exc
        provenance = SolverRuntimeProvenanceV2.from_dict(provenance_row["provenance"])
        evaluation = self._evaluation_from_document(evaluation_row["evaluation"])
        run = ReproducibilityRun(
            result,
            outcome,
            provenance,
            evaluation,
            semantic_projection_fingerprint=semantic_projection_fingerprint,
            proof_fingerprint=proof_fingerprint,
            artifact_fingerprint=artifact_fingerprint,
            metadata=dict(metadata or {}),
        )
        projection = self._require_valid_reproducibility_projection()
        prior = projection["runs"].get(run.run_id)
        if prior is not None:
            if prior["run"]["fingerprint"] != run.fingerprint:
                raise ValueError(f"reproducibility run identity collision: {run.run_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((
            result_evidence_id,
            str(outcome_row["evidence_id"]),
            str(provenance_row["evidence_id"]),
            str(evaluation_row["evidence_id"]),
            *map(str, evidence_ids),
        ))))
        evidence_id = self._record_reproducibility_document(
            record_type="RUN",
            object_id=run.run_id,
            document=run.to_dict(),
            source=REPRODUCIBILITY_RUN_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"run": run.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def certify_reproducibility(
        self,
        left_run_id: str,
        right_run_id: str,
        *,
        evidence_ids: Sequence[str] = (),
        reason: str = "reproducibility certified",
    ) -> dict[str, Any]:
        projection = self._require_valid_reproducibility_projection()
        try:
            left_row = projection["runs"][left_run_id]
            right_row = projection["runs"][right_run_id]
        except KeyError as exc:
            raise KeyError("unknown durable reproducibility run") from exc
        left = self._materialize_reproducibility_run(left_row["run"])
        right = self._materialize_reproducibility_run(right_row["run"])
        certificate = compare_reproducibility_runs(left, right)
        prior = projection["certificates"].get(certificate.certificate_id)
        if prior is not None:
            if prior["certificate"]["fingerprint"] != certificate.fingerprint:
                raise ValueError(f"reproducibility certificate collision: {certificate.certificate_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((
            str(left_row["evidence_id"]),
            str(right_row["evidence_id"]),
            *map(str, evidence_ids),
        ))))
        evidence_id = self._record_reproducibility_document(
            record_type="CERTIFICATE",
            object_id=certificate.certificate_id,
            document=certificate.to_dict(),
            source=REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"certificate": certificate.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def reproducibility_report(self) -> dict[str, Any]:
        return self._reproducibility_projection()


__all__ = [
    "REPRODUCIBILITY_RUNTIME_CONTRACT_ID",
    "REPRODUCIBILITY_RUNTIME_CONTRACT_VERSION",
    "reproducibility_runtime_contract",
    "project_reproducibility_evidence",
    "ReproducibilityRuntimeMixin",
]
