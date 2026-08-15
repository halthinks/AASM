from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from .evidence import EvidenceRecord
from .optimization import OptimizationRequest, OptimizationResult
from .provider_status_v2 import default_provider_status_map, map_provider_status
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
SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION = "0.2.0"
SOLVER_OUTCOME_V2_RUNTIME_STABILITY = "QUALIFICATION_CANDIDATE"
_SOLVER_OUTCOME_RECORD_TYPE = "aasm_solver_outcome_v2_record_type"
_SOLVER_OUTCOME_DOCUMENT = "document"
_VALIDATION_RECORD_TYPE = "aasm_solver_incumbent_validation_v2"


def solver_outcome_v2_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_OUTCOME_V2_RUNTIME_STABILITY,
        "outcome_contract": solver_outcome_v2_contract(),
        "source_result": "EXISTING_DURABLE_OPTIMIZATION_RESULT_REQUIRED",
        "source_request": "EXACT_DURABLE_OPTIMIZATION_REQUEST_REQUIRED",
        "source_binding": "EXACT_REQUEST_RESULT_MODEL_AND_FINGERPRINT",
        "provider_mapping": "EXACT_VERSIONED_PROVIDER_STATUS_MAP",
        "incumbent_validation": "AASM_VALIDATE_OPTIMIZATION_SOLUTION_BEFORE_ACCEPTANCE",
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "parallel_result_table": "NONE",
        "normalization_grants_truth": False,
        "validation_evidence": "DURABLE_LOCAL_EVIDENCE_DERIVED_FROM_SOURCE_RESULT",
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
            issues.append({"index": index, "evidence_id": evidence_id, "error": f"{type(exc).__name__}: {exc}"})
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

    def _durable_optimization_request(self, request_id: str) -> OptimizationRequest:
        return OptimizationRequest.from_dict(self.optimization_request_report(request_id)["request"])

    def _existing_outcome_for_source(self, result_id: str) -> dict[str, Any] | None:
        projection = self._require_valid_solver_outcome_v2_projection()
        matches = [row for row in projection["outcomes"].values() if row["outcome"].get("source_result_id") == result_id]
        if len(matches) > 1:
            raise RuntimeError(f"multiple solver outcome v2 records bind source result {result_id}")
        return deepcopy(matches[0]) if matches else None

    def _record_incumbent_validation(self, source: OptimizationResult, source_evidence_id: str, request: OptimizationRequest) -> str:
        # normalize_optimization_result_v2 performs the actual independent model/assignment/objective check.
        probe = normalize_optimization_result_v2(source, request=request)
        if probe.incumbent_validation != "VALIDATED":
            raise ValueError("incumbent validation Evidence requested for a result without a validated incumbent")
        document = {
            "contract_id": "aasm.solver.incumbent-validation.v1",
            "contract_version": "0.1.0",
            "checker_id": "aasm.optimization.validate_optimization_solution",
            "source_result_id": source.result_id,
            "source_result_fingerprint": source.fingerprint,
            "request_id": request.request_id,
            "request_fingerprint": request.fingerprint,
            "model_fingerprint": request.model.fingerprint,
            "assignment_fingerprint": probe.assignment_fingerprint,
            "status": "PASS",
        }
        evidence_id = f"solver-incumbent-validation-{semantic_fingerprint(document)[:24]}"
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        prior = next((row for row in records if row.get("evidence_id") == evidence_id and row.get("status", "active") == "active"), None)
        if prior is not None:
            if json.loads(str(prior.get("statement") or "{}")) != document:
                raise ValueError("solver incumbent validation Evidence identity collision")
            return evidence_id
        record = EvidenceRecord(
            kind="solver_incumbent_validation_v2",
            statement=canonical_semantic_json(document),
            source=SOLVER_OUTCOME_V2_CONTRACT_ID,
            derived_from=[source_evidence_id],
            metadata={
                _VALIDATION_RECORD_TYPE: True,
                "source_result_id": source.result_id,
                "assignment_fingerprint": probe.assignment_fingerprint,
                "checker_id": document["checker_id"],
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason="solver incumbent independently validated")
        return evidence_id

    def record_solver_outcome_v2(
        self,
        result_id: str,
        *,
        termination: ProviderTermination | Mapping[str, Any] | None = None,
        evidence: SolverEvidenceGrade | Mapping[str, Any] | None = None,
        normalized_status: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        reason: str = "solver outcome v2 normalized",
    ) -> dict[str, Any]:
        prior = self._existing_outcome_for_source(result_id)
        if prior is not None and termination is None and evidence is None and normalized_status is None and not metadata:
            return {**prior, "already_recorded": True}
        source, source_evidence_id = self._durable_optimization_result(result_id)
        request = self._durable_optimization_request(source.request_id)
        if source.request_fingerprint != request.fingerprint or source.model_fingerprint != request.model.fingerprint:
            raise ValueError("durable optimization result is stale or misbound to its request/model")

        raw_status = str(source.statistics.get("raw_status") or source.status)
        raw_status_code = str(source.statistics.get("raw_status_code") or "")
        mapping = None
        effective_termination = termination
        effective_status = normalized_status
        provider_rule_id = ""
        provider_map_version = ""
        if termination is None or normalized_status is None:
            status_map = default_provider_status_map(source.solver.provider_id, source.solver.version)
            mapping = map_provider_status(
                status_map,
                raw_status=raw_status,
                raw_status_code=raw_status_code,
                raw_message="; ".join(source.diagnostics),
                has_incumbent=bool(source.assignment),
                objective_present=request.model.objective is not None,
                limit_value=request.timeout_ms / 1000.0 if raw_status in {"kTimeLimit", "UNKNOWN"} else None,
                metadata={"source_result_id": source.result_id},
            )
            if effective_termination is None:
                effective_termination = mapping.termination
            if effective_status is None:
                effective_status = mapping.normalized_status
            provider_rule_id = mapping.rule_id
            provider_map_version = mapping.map_version

        grade = None if evidence is None else (
            evidence if isinstance(evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(evidence)
        )
        local_validation_ids = () if grade is None else self._require_evidence_ids(grade.validation_evidence_ids)
        if source.assignment and grade is None:
            validation_evidence_id = self._record_incumbent_validation(source, source_evidence_id, request)
            grade = SolverEvidenceGrade(
                "INDEPENDENTLY_VALIDATED",
                "NO_CERTIFICATE",
                checker_ids=("aasm.optimization.validate_optimization_solution",),
                validation_evidence_ids=(validation_evidence_id,),
            )
            local_validation_ids = (validation_evidence_id,)

        outcome = normalize_optimization_result_v2(
            source,
            request=request,
            termination=effective_termination,
            normalized_status=effective_status,
            evidence=grade,
            provider_status_rule_id=provider_rule_id,
            provider_status_map_version=provider_map_version,
            metadata={"provider_mapping": mapping.to_dict() if mapping else None, **dict(metadata or {})},
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
                "normalized_status": outcome.normalized_status,
                "legacy_status": outcome.legacy_projection.status,
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
        return {"runtime_contract": projection["runtime_contract"], "valid": projection["valid"], "issues": projection["issues"], **deepcopy(row)}


__all__ = [
    "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID", "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION",
    "SOLVER_OUTCOME_V2_RUNTIME_STABILITY", "solver_outcome_v2_runtime_contract",
    "project_solver_outcome_v2_evidence", "SolverOutcomeV2RuntimeMixin",
]
