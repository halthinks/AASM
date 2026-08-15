from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from .evidence import EvidenceRecord
from .optimization import OptimizationResult
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_outcome_v2 import (
    SOLVER_OUTCOME_V2_CONTRACT_ID,
    ProviderTermination,
    SolverEvidenceGrade,
    SolverOutcomeV2,
    normalize_optimization_result_v2,
    solver_outcome_v2_contract,
)


SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID = "aasm.solver.outcome-v2.runtime.v1"
SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOLVER_OUTCOME_V2_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_SOLVER_OUTCOME_RECORD_TYPE = "aasm_solver_outcome_v2_record_type"
_SOLVER_OUTCOME_DOCUMENT = "document"


def solver_outcome_v2_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_OUTCOME_V2_RUNTIME_STABILITY,
        "outcome_contract": solver_outcome_v2_contract(),
        "source_result": "EXISTING_DURABLE_OPTIMIZATION_RESULT_REQUIRED",
        "source_binding": "EXACT_RESULT_ID_AND_FINGERPRINT",
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "parallel_result_table": "NONE",
        "normalization_grants_truth": False,
        "validation_evidence": "LOCAL_EVIDENCE_IDS_ONLY",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "NONE",
    }


def _outcome_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(_SOLVER_OUTCOME_DOCUMENT)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("solver outcome v2 Evidence is missing canonical document")


def project_solver_outcome_v2_evidence(records) -> dict[str, Any]:
    outcomes: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_SOLVER_OUTCOME_RECORD_TYPE) != "OUTCOME_V2":
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            outcome = SolverOutcomeV2.from_dict(_outcome_document(row))
            if metadata.get("outcome_id") != outcome.outcome_id:
                raise ValueError("solver outcome v2 metadata outcome_id mismatch")
            if metadata.get("outcome_fingerprint") != outcome.fingerprint:
                raise ValueError("solver outcome v2 metadata fingerprint mismatch")
            prior = outcomes.get(outcome.outcome_id)
            candidate = {"outcome": outcome.to_dict(), "evidence_id": evidence_id}
            if prior is not None and prior != candidate:
                raise ValueError(f"solver outcome v2 identity collision: {outcome.outcome_id}")
            outcomes[outcome.outcome_id] = candidate
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return {
        "runtime_contract": solver_outcome_v2_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "outcomes": outcomes,
    }


class SolverOutcomeV2RuntimeMixin:
    def solver_outcome_v2_runtime_contract_report(self) -> dict[str, Any]:
        return solver_outcome_v2_runtime_contract()

    def _solver_outcome_v2_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_solver_outcome_v2_evidence(records)

    def _require_valid_solver_outcome_v2_projection(self) -> dict[str, Any]:
        report = self._solver_outcome_v2_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable solver outcome v2 projection: {report['issues']}")
        return report

    def _durable_optimization_result(self, result_id: str) -> tuple[OptimizationResult, str]:
        report = self.optimization_result_report()
        matches = []
        for rows in report.get("results", {}).values():
            for row in rows:
                result = OptimizationResult.from_dict(row["result"])
                if result.result_id == result_id:
                    matches.append((result, str(row["evidence_id"])))
        if not matches:
            raise KeyError(f"unknown durable optimization result: {result_id}")
        if len(matches) != 1:
            raise RuntimeError(f"duplicate durable optimization result identity: {result_id}")
        return matches[0]

    def record_solver_outcome_v2(
        self,
        result_id: str,
        *,
        termination: ProviderTermination | Mapping[str, Any] | None = None,
        evidence: SolverEvidenceGrade | Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        reason: str = "solver outcome v2 normalized",
    ) -> dict[str, Any]:
        source, source_evidence_id = self._durable_optimization_result(result_id)
        grade = None if evidence is None else (
            evidence if isinstance(evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(evidence)
        )
        validation_ids = () if grade is None else grade.validation_evidence_ids
        local_validation_ids = self._require_evidence_ids(validation_ids)
        outcome = normalize_optimization_result_v2(
            source,
            termination=termination,
            evidence=grade,
            metadata=metadata,
        )
        projection = self._require_valid_solver_outcome_v2_projection()
        prior = projection["outcomes"].get(outcome.outcome_id)
        if prior is not None:
            prior_outcome = SolverOutcomeV2.from_dict(prior["outcome"])
            if prior_outcome.fingerprint != outcome.fingerprint:
                raise ValueError(f"solver outcome v2 identity collision: {outcome.outcome_id}")
            return {**deepcopy(prior), "already_recorded": True}
        document = outcome.to_dict()
        evidence_id = f"solver-outcome-v2-evidence-{semantic_fingerprint(document)[:24]}"
        lineage = tuple(sorted(set((source_evidence_id, *local_validation_ids))))
        record = EvidenceRecord(
            kind="solver_outcome_v2",
            statement=canonical_semantic_json(document),
            source=SOLVER_OUTCOME_V2_CONTRACT_ID,
            derived_from=list(lineage),
            metadata={
                _SOLVER_OUTCOME_RECORD_TYPE: "OUTCOME_V2",
                _SOLVER_OUTCOME_DOCUMENT: document,
                "outcome_id": outcome.outcome_id,
                "outcome_fingerprint": outcome.fingerprint,
                "source_result_id": source.result_id,
                "source_result_fingerprint": source.fingerprint,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return {"outcome": outcome.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def solver_outcome_v2_report(self, outcome_id: str | None = None) -> dict[str, Any]:
        projection = self._solver_outcome_v2_projection()
        if outcome_id is None:
            return projection
        try:
            row = projection["outcomes"][outcome_id]
        except KeyError:
            raise KeyError(outcome_id) from None
        return {
            "runtime_contract": projection["runtime_contract"],
            "valid": projection["valid"],
            "issues": projection["issues"],
            **deepcopy(row),
        }


__all__ = [
    "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID",
    "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION",
    "SOLVER_OUTCOME_V2_RUNTIME_STABILITY",
    "solver_outcome_v2_runtime_contract",
    "project_solver_outcome_v2_evidence",
    "SolverOutcomeV2RuntimeMixin",
]
