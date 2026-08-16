from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .convex_optimization import ConvexOptimizationRequest, ConvexOptimizationResult
from .evidence import EvidenceRecord
from .optimization import OptimizationRequest
from .provider_status_v2 import default_provider_status_map
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_execution_observation import (
    SolverExecutionObservation,
    execution_observation_for_convex,
    execution_observation_for_optimization,
)
from .solver_outcome_v2 import SolverOutcomeV2
from .solver_provenance import (
    SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
    SOLVER_PROFILE_EVALUATION_CONTRACT_ID,
    SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID,
    SolverExecutionProfile,
    SolverProfileEvaluation,
    SolverRuntimeProvenance,
    build_solver_runtime_provenance,
    evaluate_solver_execution_profile,
    solver_provenance_contract,
)


SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID = "aasm.solver.runtime-provenance.runtime.v1"
SOLVER_PROVENANCE_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOLVER_PROVENANCE_RUNTIME_STABILITY = "QUALIFICATION_CANDIDATE"
_PROVENANCE_RECORD_TYPE = "aasm_solver_provenance_record_type"
_PROVENANCE_DOCUMENT = "document"


def solver_provenance_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_PROVENANCE_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_PROVENANCE_RUNTIME_STABILITY,
        "provenance_contract": solver_provenance_contract(),
        "profile_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "provenance_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "evaluation_durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "source_result": "EXACT_DURABLE_PROVIDER_RESULT_REQUIRED",
        "source_outcome": "EXACT_DURABLE_SOLVER_OUTCOME_V2_REQUIRED_FOR_V44_OPTIMIZATION",
        "effective_configuration_source": "AASM_PROVIDER_ADAPTER_OBSERVATION_NOT_CALLER_ASSERTION",
        "provider_status_map": "EXACT_V056_PROVIDER_STATUS_MAP_FINGERPRINT_BOUND_WHERE_APPLICABLE",
        "parallel_provenance_table": "NONE",
        "profile_grants_authority": False,
        "provenance_grants_reproducibility": False,
        "truth_authority": "NONE",
        "policy_authority": "NONE",
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
    raise ValueError("solver provenance Evidence is missing canonical document")


def project_solver_provenance_evidence(records) -> dict[str, Any]:
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
        if record_type not in {"PROFILE", "PROVENANCE", "PROFILE_EVALUATION"}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == "PROFILE":
                item = SolverExecutionProfile.from_dict(document)
                object_id, fingerprint, target, payload_key = item.profile_id, item.fingerprint, profiles, "profile"
            elif record_type == "PROVENANCE":
                item = SolverRuntimeProvenance.from_dict(document)
                object_id, fingerprint, target, payload_key = item.provenance_id, item.fingerprint, provenances, "provenance"
            else:
                item = SolverProfileEvaluation.from_dict(document)
                object_id, fingerprint, target, payload_key = item.evaluation_id, item.fingerprint, evaluations, "evaluation"
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
            issues.append({"index": index, "evidence_id": evidence_id, "record_type": record_type, "error": f"{type(exc).__name__}: {exc}"})
    return {
        "runtime_contract": solver_provenance_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "profiles": profiles,
        "provenances": provenances,
        "evaluations": evaluations,
    }


def _provenance_from_observation(
    *,
    result,
    outcome: SolverOutcomeV2 | None,
    profile: SolverExecutionProfile,
    execution_id: str,
    observation: SolverExecutionObservation,
    provider_status_map_id: str = "",
    provider_status_map_fingerprint: str = "",
) -> SolverRuntimeProvenance:
    if outcome is not None:
        return build_solver_runtime_provenance(
            result,
            outcome,
            profile,
            execution_id=execution_id,
            adapter_id=observation.adapter_id,
            adapter_version=observation.adapter_version,
            effective_options=observation.effective_options,
            worker_count=observation.worker_count,
            thread_count=observation.thread_count,
            environment_fingerprint=observation.environment_fingerprint,
            platform_identity=observation.platform_identity,
            library_identity=observation.library_identity,
            build_fingerprint=observation.build_fingerprint,
            formulation_id=observation.formulation_id,
            formulation_fingerprint=observation.formulation_fingerprint,
            problem_revision_id=observation.problem_revision_id,
            problem_revision_fingerprint=observation.problem_revision_fingerprint,
            provider_status_map_id=provider_status_map_id,
            provider_status_map_fingerprint=provider_status_map_fingerprint,
            numeric_policy_id=observation.numeric_policy_id,
            numeric_policy_fingerprint=observation.numeric_policy_fingerprint,
            metadata=observation.metadata,
        )
    solver = result.solver
    if profile.provider_id and profile.provider_id != solver.provider_id:
        raise ValueError("solver execution profile provider_id does not match convex result provider")
    if profile.provider_version and profile.provider_version != solver.version:
        raise ValueError("solver execution profile provider_version does not match convex result provider version")
    if profile.adapter_id and profile.adapter_id != observation.adapter_id:
        raise ValueError("solver execution profile adapter_id does not match convex runtime adapter")
    if profile.adapter_version and profile.adapter_version != observation.adapter_version:
        raise ValueError("solver execution profile adapter_version does not match convex runtime adapter version")
    if profile.required_environment_fingerprint and profile.required_environment_fingerprint != observation.environment_fingerprint:
        raise ValueError("solver execution profile required environment fingerprint mismatch")
    return SolverRuntimeProvenance(
        execution_id=execution_id,
        source_result_id=result.result_id,
        source_result_fingerprint=result.fingerprint,
        source_outcome_id="",
        source_outcome_fingerprint="",
        profile_id=profile.profile_id,
        profile_fingerprint=profile.fingerprint,
        model_fingerprint=result.model_fingerprint,
        provider_id=solver.provider_id,
        provider_implementation=solver.implementation,
        provider_version=solver.version,
        adapter_id=observation.adapter_id,
        adapter_version=observation.adapter_version,
        solver_command=(solver.implementation, solver.backend_solver),
        requested_options=profile.requested_options,
        effective_options=observation.effective_options,
        worker_count=observation.worker_count,
        thread_count=observation.thread_count,
        environment_fingerprint=observation.environment_fingerprint,
        platform_identity=observation.platform_identity,
        library_identity=observation.library_identity,
        build_fingerprint=observation.build_fingerprint,
        formulation_id=observation.formulation_id,
        formulation_fingerprint=observation.formulation_fingerprint,
        problem_revision_id=observation.problem_revision_id,
        problem_revision_fingerprint=observation.problem_revision_fingerprint,
        numeric_policy_id=observation.numeric_policy_id,
        numeric_policy_fingerprint=observation.numeric_policy_fingerprint,
        dependency_fingerprints=tuple(result.statistics.get("dependency_fingerprints") or ()),
        metadata=observation.metadata,
    )


class SolverProvenanceRuntimeMixin:
    def solver_provenance_runtime_contract_report(self) -> dict[str, Any]:
        return solver_provenance_runtime_contract()

    def _solver_provenance_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_solver_provenance_evidence(records)

    def _require_valid_solver_provenance_projection(self) -> dict[str, Any]:
        report = self._solver_provenance_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable solver provenance projection: {report['issues']}")
        return report

    def _record_solver_provenance_document(self, *, record_type: str, object_id: str, object_fingerprint: str, document: Mapping[str, Any], source: str, derived_from: Sequence[str], reason: str) -> str:
        payload = deepcopy(dict(document))
        evidence_id = f"solver-provenance-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_PROVENANCE_RECORD_TYPE) != record_type or metadata.get(_PROVENANCE_DOCUMENT) != payload:
                raise ValueError(f"solver provenance Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="solver_provenance",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={_PROVENANCE_RECORD_TYPE: record_type, _PROVENANCE_DOCUMENT: payload, "object_id": object_id, "object_fingerprint": object_fingerprint, "authority": "EVIDENCE_ONLY"},
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def register_solver_execution_profile(self, profile: SolverExecutionProfile | Mapping[str, Any], *, evidence_ids: Sequence[str] = (), reason: str = "solver execution profile registered") -> dict[str, Any]:
        item = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
        projection = self._require_valid_solver_provenance_projection()
        prior = projection["profiles"].get(item.profile_id)
        if prior is not None:
            if prior["profile"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"solver execution profile identity collision: {item.profile_id}")
            return {**deepcopy(prior), "already_registered": True}
        evidence_id = self._record_solver_provenance_document(record_type="PROFILE", object_id=item.profile_id, object_fingerprint=item.fingerprint, document=item.to_dict(), source=SOLVER_EXECUTION_PROFILE_CONTRACT_ID, derived_from=tuple(evidence_ids), reason=reason)
        return {"profile": item.to_dict(), "evidence_id": evidence_id, "already_registered": False}

    def _profile(self, profile_id: str) -> tuple[SolverExecutionProfile, dict[str, Any]]:
        projection = self._require_valid_solver_provenance_projection()
        try:
            row = projection["profiles"][profile_id]
        except KeyError:
            raise KeyError(f"unknown durable solver execution profile: {profile_id}") from None
        return SolverExecutionProfile.from_dict(row["profile"]), row

    def record_solver_runtime_provenance(self, result_id: str, outcome_id: str, profile_id: str, *, execution_id: str, evidence_ids: Sequence[str] = (), reason: str = "solver runtime provenance recorded") -> dict[str, Any]:
        source, source_evidence_id = self._durable_optimization_result(result_id)
        request_row = self.optimization_request_report(source.request_id)
        request = OptimizationRequest.from_dict(request_row["request"])
        outcome_row = self.solver_outcome_v2_report(outcome_id)
        outcome = SolverOutcomeV2.from_dict(outcome_row["outcome"])
        if outcome.source_result_id != source.result_id or outcome.source_result_fingerprint != source.fingerprint:
            raise ValueError("solver runtime provenance source outcome does not bind exact source result")
        profile, profile_row = self._profile(profile_id)
        observation = execution_observation_for_optimization(request, source)
        status_map = default_provider_status_map(source.solver.provider_id, source.solver.version)
        provenance = _provenance_from_observation(result=source, outcome=outcome, profile=profile, execution_id=execution_id, observation=observation, provider_status_map_id=status_map.map_id, provider_status_map_fingerprint=status_map.fingerprint)
        projection = self._require_valid_solver_provenance_projection()
        prior = projection["provenances"].get(provenance.provenance_id)
        if prior is not None:
            if prior["provenance"]["fingerprint"] != provenance.fingerprint:
                raise ValueError(f"solver runtime provenance identity collision: {provenance.provenance_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((source_evidence_id, str(request_row["evidence_id"]), str(outcome_row["evidence_id"]), str(profile_row["evidence_id"]), *map(str, evidence_ids)))))
        evidence_id = self._record_solver_provenance_document(record_type="PROVENANCE", object_id=provenance.provenance_id, object_fingerprint=provenance.fingerprint, document=provenance.to_dict(), source=SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID, derived_from=lineage, reason=reason)
        return {"provenance": provenance.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def _durable_convex_result(self, result_id: str) -> tuple[ConvexOptimizationResult, str, ConvexOptimizationRequest, str]:
        for request_id, rows in self.convex_result_report()["results"].items():
            for row in rows:
                result = ConvexOptimizationResult.from_dict(row["result"])
                if result.result_id != result_id:
                    continue
                request_row = self.convex_request_report(request_id)
                return result, str(row["evidence_id"]), ConvexOptimizationRequest.from_dict(request_row["request"]), str(request_row["evidence_id"])
        raise KeyError(f"unknown durable convex optimization result: {result_id}")

    def record_convex_solver_runtime_provenance(self, result_id: str, profile_id: str, *, execution_id: str, evidence_ids: Sequence[str] = (), reason: str = "convex solver runtime provenance recorded") -> dict[str, Any]:
        result, result_evidence_id, request, request_evidence_id = self._durable_convex_result(result_id)
        profile, profile_row = self._profile(profile_id)
        observation = execution_observation_for_convex(request, result)
        provenance = _provenance_from_observation(result=result, outcome=None, profile=profile, execution_id=execution_id, observation=observation)
        projection = self._require_valid_solver_provenance_projection()
        prior = projection["provenances"].get(provenance.provenance_id)
        if prior is not None:
            if prior["provenance"]["fingerprint"] != provenance.fingerprint:
                raise ValueError(f"solver runtime provenance identity collision: {provenance.provenance_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((result_evidence_id, request_evidence_id, str(profile_row["evidence_id"]), *map(str, evidence_ids)))))
        evidence_id = self._record_solver_provenance_document(record_type="PROVENANCE", object_id=provenance.provenance_id, object_fingerprint=provenance.fingerprint, document=provenance.to_dict(), source=SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID, derived_from=lineage, reason=reason)
        return {"provenance": provenance.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def evaluate_solver_runtime_profile(self, provenance_id: str, *, evidence_ids: Sequence[str] = (), reason: str = "solver runtime profile evaluated") -> dict[str, Any]:
        projection = self._require_valid_solver_provenance_projection()
        try:
            provenance_row = projection["provenances"][provenance_id]
        except KeyError:
            raise KeyError(provenance_id) from None
        provenance = SolverRuntimeProvenance.from_dict(provenance_row["provenance"])
        profile, profile_row = self._profile(provenance.profile_id)
        evaluation = evaluate_solver_execution_profile(profile, provenance)
        prior = projection["evaluations"].get(evaluation.evaluation_id)
        if prior is not None:
            if prior["evaluation"]["fingerprint"] != evaluation.fingerprint:
                raise ValueError(f"solver profile evaluation identity collision: {evaluation.evaluation_id}")
            return {**deepcopy(prior), "already_recorded": True}
        lineage = tuple(sorted(set((str(provenance_row["evidence_id"]), str(profile_row["evidence_id"]), *map(str, evidence_ids)))))
        evidence_id = self._record_solver_provenance_document(record_type="PROFILE_EVALUATION", object_id=evaluation.evaluation_id, object_fingerprint=evaluation.fingerprint, document=evaluation.to_dict(), source=SOLVER_PROFILE_EVALUATION_CONTRACT_ID, derived_from=lineage, reason=reason)
        return {"evaluation": evaluation.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def solver_provenance_report(self) -> dict[str, Any]:
        return self._solver_provenance_projection()


__all__ = [
    "SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID", "SOLVER_PROVENANCE_RUNTIME_CONTRACT_VERSION",
    "solver_provenance_runtime_contract", "project_solver_provenance_evidence", "SolverProvenanceRuntimeMixin",
]
