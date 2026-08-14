from __future__ import annotations

from typing import Any, Mapping

from .evidence import EvidenceRecord
from .optimization import OptimizationModel, objective_value, validate_optimization_solution
from .semantic_result import semantic_fingerprint
from .solution_pools import (
    ENUMERATION_CONTRACT_ID,
    SOLUTION_POOL_CONTRACT_ID,
    EnumerationCompletenessCertificate,
    EnumerationCursor,
    EnumerationUnsupportedError,
    SolutionExclusion,
    SolutionPool,
    SolutionRecord,
    certify_complete_finite_enumeration,
    enumerate_finite_step,
    enumeration_contract,
    initial_enumeration_cursor,
    solution_pool_contract,
)


def _pool_records(snapshot):
    return list(snapshot.evidence.get("records", []))


def _pool_projection(snapshot, record_type: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for value in _pool_records(snapshot):
        metadata = value.get("metadata") or {}
        if metadata.get("solution_pool_record_type") != record_type:
            continue
        object_id = str(metadata.get("object_id") or value.get("evidence_id") or "")
        out[object_id] = metadata.get("document") or {}
    return out


class SolutionPoolRuntimeMixin:
    """v0.51 governed solution pools over the existing Evidence/event history."""

    def solution_pool_contract_report(self) -> dict[str, Any]:
        return solution_pool_contract()

    def enumeration_contract_report(self) -> dict[str, Any]:
        return enumeration_contract()

    def _record_solution_pool_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
    ) -> str:
        payload = dict(document)
        evidence_id = f"solution-pool-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        for row in _pool_records(self.snapshot):
            if row.get("evidence_id") == evidence_id:
                metadata = row.get("metadata") or {}
                if metadata.get("solution_pool_record_type") != record_type or metadata.get("document") != payload:
                    raise ValueError(f"solution-pool evidence collision: {evidence_id}")
                return evidence_id
        self.add_evidence(EvidenceRecord(
            kind="optimization_result",
            statement=f"AASM {record_type}: {object_id}",
            source=source,
            derived_from=list(derived_from),
            metadata={
                "solution_pool_record_type": record_type,
                "object_id": object_id,
                "document": payload,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        ))
        return evidence_id

    def solution_pool_report(self, pool_id: str | None = None) -> dict[str, Any]:
        pools = _pool_projection(self.snapshot, "solution_pool")
        cursors = _pool_projection(self.snapshot, "enumeration_cursor")
        solutions = _pool_projection(self.snapshot, "solution_record")
        exclusions = _pool_projection(self.snapshot, "solution_exclusion")
        certificates = _pool_projection(self.snapshot, "enumeration_completeness_certificate")
        report = {
            "contract": solution_pool_contract(),
            "enumeration_contract": enumeration_contract(),
            "pools": pools,
            "cursors": cursors,
            "solutions": solutions,
            "exclusions": exclusions,
            "completeness_certificates": certificates,
        }
        if pool_id is None:
            return report
        if pool_id not in pools:
            raise KeyError(pool_id)
        pool = pools[pool_id]
        report["pool"] = pool
        report["cursor"] = cursors.get(pool_id)
        solution_ids = set(pool.get("solution_ids") or [])
        report["pool_solutions"] = {key: value for key, value in solutions.items() if key in solution_ids}
        exclusion_ids = set(pool.get("exclusion_ids") or [])
        report["pool_exclusions"] = {key: value for key, value in exclusions.items() if key in exclusion_ids}
        certificate_id = str(pool.get("completeness_certificate_id") or "")
        report["completeness_certificate"] = certificates.get(certificate_id) if certificate_id else None
        return report

    def start_solution_pool(
        self,
        model: OptimizationModel,
        *,
        mode: str = "COMPLETE_FINITE_ENUMERATION",
        lineage: Mapping[str, Any] | None = None,
        max_total_states: int = 100_000,
    ) -> dict[str, Any]:
        lineage = dict(lineage or {})
        pool = SolutionPool(model.fingerprint, mode, lineage=lineage)
        existing = _pool_projection(self.snapshot, "solution_pool").get(pool.pool_id)
        if existing is not None:
            if existing.get("model_fingerprint") != model.fingerprint or existing.get("mode") != mode:
                raise ValueError("existing solution pool identity conflicts with requested pool")
            return {"already_exists": True, **self.solution_pool_report(pool.pool_id)}
        cursor = None
        if mode in {"COMPLETE_FINITE_ENUMERATION", "BOUNDED_PARTIAL_POOL"}:
            cursor = initial_enumeration_cursor(model, pool.pool_id, mode, max_total_states=max_total_states)
            pool = SolutionPool(
                model.fingerprint,
                mode,
                cursor_fingerprint=cursor.fingerprint,
                lineage=lineage,
                pool_id=pool.pool_id,
            )
        pool_evidence_id = self._record_solution_pool_document(
            record_type="solution_pool",
            object_id=pool.pool_id,
            document=pool.to_dict(),
            source=SOLUTION_POOL_CONTRACT_ID,
        )
        cursor_evidence_id = ""
        if cursor is not None:
            cursor_evidence_id = self._record_solution_pool_document(
                record_type="enumeration_cursor",
                object_id=pool.pool_id,
                document=cursor.to_dict(),
                source=ENUMERATION_CONTRACT_ID,
                derived_from=(pool_evidence_id,),
            )
        return {
            "already_exists": False,
            "pool": pool.to_dict(),
            "cursor": cursor.to_dict() if cursor else None,
            "pool_evidence_id": pool_evidence_id,
            "cursor_evidence_id": cursor_evidence_id,
        }

    def admit_solution_to_pool(
        self,
        pool_id: str,
        model: OptimizationModel,
        assignment: Mapping[str, float],
        *,
        solver_provider_id: str,
        lineage_ids=(),
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        current_doc = _pool_projection(self.snapshot, "solution_pool").get(pool_id)
        if current_doc is None:
            raise KeyError(pool_id)
        pool = SolutionPool.from_dict(current_doc)
        if pool.model_fingerprint != model.fingerprint:
            raise ValueError("solution pool/model fingerprint mismatch")
        if pool.mode == "COMPLETE_FINITE_ENUMERATION":
            raise ValueError("manual solution admission is not allowed in COMPLETE_FINITE_ENUMERATION mode")
        validate_optimization_solution(model, assignment)
        record = SolutionRecord(
            model.fingerprint,
            assignment,
            solver_provider_id=solver_provider_id,
            objective=objective_value(model, assignment),
            lineage_ids=tuple(lineage_ids),
            metadata=dict(metadata or {}),
        )
        existing = {row.solution_id: row for row in pool.solutions}
        if record.solution_id in existing:
            return {"already_present": True, "solution": existing[record.solution_id].to_dict(), "pool": pool.to_dict()}
        exclusion = SolutionExclusion(pool.pool_id, model.fingerprint, record.solution_id, record.assignment)
        solution_evidence_id = self._record_solution_pool_document(
            record_type="solution_record",
            object_id=record.solution_id,
            document=record.to_dict(),
            source=solver_provider_id,
            derived_from=tuple(lineage_ids),
        )
        exclusion_evidence_id = self._record_solution_pool_document(
            record_type="solution_exclusion",
            object_id=exclusion.exclusion_id,
            document=exclusion.to_dict(),
            source=SOLUTION_POOL_CONTRACT_ID,
            derived_from=(solution_evidence_id,),
        )
        updated = SolutionPool(
            model.fingerprint,
            pool.mode,
            solutions=tuple([*pool.solutions, record]),
            exclusion_ids=tuple([*pool.exclusion_ids, exclusion.exclusion_id]),
            completeness_status="PARTIAL_NON_EXHAUSTIVE",
            cursor_fingerprint=pool.cursor_fingerprint,
            lineage=pool.lineage,
            pool_id=pool.pool_id,
        )
        pool_evidence_id = self._record_solution_pool_document(
            record_type="solution_pool",
            object_id=pool.pool_id,
            document=updated.to_dict(),
            source=SOLUTION_POOL_CONTRACT_ID,
            derived_from=(solution_evidence_id, exclusion_evidence_id),
        )
        return {"already_present": False, "solution": record.to_dict(), "exclusion": exclusion.to_dict(), "pool": updated.to_dict(), "pool_evidence_id": pool_evidence_id}

    def advance_solution_pool(
        self,
        pool_id: str,
        model: OptimizationModel,
        *,
        max_states_per_step: int = 1_000,
        max_total_states: int = 100_000,
    ) -> dict[str, Any]:
        pools = _pool_projection(self.snapshot, "solution_pool")
        cursors = _pool_projection(self.snapshot, "enumeration_cursor")
        if pool_id not in pools:
            raise KeyError(pool_id)
        pool = SolutionPool.from_dict(pools[pool_id])
        if pool.model_fingerprint != model.fingerprint:
            raise ValueError("solution pool/model fingerprint mismatch")
        if pool.mode not in {"COMPLETE_FINITE_ENUMERATION", "BOUNDED_PARTIAL_POOL"}:
            raise ValueError(f"mode {pool.mode} does not support deterministic finite cursor advancement")
        cursor_doc = cursors.get(pool_id)
        if cursor_doc is None:
            raise ValueError("enumeration pool is missing durable cursor")
        cursor = EnumerationCursor.from_dict(cursor_doc)
        if pool.completeness_status == "COMPLETE":
            return {"already_complete": True, **self.solution_pool_report(pool_id)}
        step = enumerate_finite_step(
            model,
            pool_id,
            cursor=cursor,
            existing_solutions=pool.solutions,
            max_states_per_step=max_states_per_step,
            max_total_states=max_total_states,
        )
        accepted: list[SolutionRecord] = step["accepted"]
        exclusions: list[SolutionExclusion] = step["exclusions"]
        derived_solution_evidence: list[str] = []
        for record, exclusion in zip(accepted, exclusions):
            sid = self._record_solution_pool_document(
                record_type="solution_record",
                object_id=record.solution_id,
                document=record.to_dict(),
                source=record.solver_provider_id,
            )
            eid = self._record_solution_pool_document(
                record_type="solution_exclusion",
                object_id=exclusion.exclusion_id,
                document=exclusion.to_dict(),
                source=ENUMERATION_CONTRACT_ID,
                derived_from=(sid,),
            )
            derived_solution_evidence.extend((sid, eid))
        next_cursor: EnumerationCursor = step["cursor"]
        cursor_evidence_id = self._record_solution_pool_document(
            record_type="enumeration_cursor",
            object_id=pool_id,
            document=next_cursor.to_dict(),
            source=ENUMERATION_CONTRACT_ID,
            derived_from=tuple(derived_solution_evidence),
        )
        combined_solutions = tuple([*pool.solutions, *accepted])
        combined_exclusions = tuple(sorted(set(pool.exclusion_ids) | {row.exclusion_id for row in exclusions}))
        status = "PARTIAL"
        if next_cursor.exhausted:
            status = "EXHAUSTED_PENDING_CERTIFICATION" if pool.mode == "COMPLETE_FINITE_ENUMERATION" else "PARTIAL_NON_EXHAUSTIVE"
        interim = SolutionPool(
            model.fingerprint,
            pool.mode,
            solutions=combined_solutions,
            exclusion_ids=combined_exclusions,
            completeness_status=status,
            cursor_fingerprint=next_cursor.fingerprint,
            lineage=pool.lineage,
            pool_id=pool.pool_id,
        )
        interim_evidence_id = self._record_solution_pool_document(
            record_type="solution_pool",
            object_id=pool_id,
            document=interim.to_dict(),
            source=SOLUTION_POOL_CONTRACT_ID,
            derived_from=(cursor_evidence_id, *derived_solution_evidence),
        )
        certificate_doc = None
        final_pool = interim
        certificate_evidence_id = ""
        if next_cursor.exhausted and pool.mode == "COMPLETE_FINITE_ENUMERATION":
            certificate = certify_complete_finite_enumeration(
                model,
                interim,
                cursor=next_cursor,
                max_total_states=max_total_states,
            )
            certificate_doc = certificate.to_dict()
            certificate_evidence_id = self._record_solution_pool_document(
                record_type="enumeration_completeness_certificate",
                object_id=certificate.certificate_id,
                document=certificate_doc,
                source=certificate.checker_id,
                derived_from=(interim_evidence_id, cursor_evidence_id),
            )
            final_pool = SolutionPool(
                model.fingerprint,
                pool.mode,
                solutions=combined_solutions,
                exclusion_ids=combined_exclusions,
                completeness_status="COMPLETE" if certificate.status == "PASS" else "FAILED_COMPLETENESS",
                cursor_fingerprint=next_cursor.fingerprint,
                completeness_certificate_id=certificate.certificate_id if certificate.status == "PASS" else "",
                lineage=pool.lineage,
                pool_id=pool.pool_id,
            )
            self._record_solution_pool_document(
                record_type="solution_pool",
                object_id=pool_id,
                document=final_pool.to_dict(),
                source=SOLUTION_POOL_CONTRACT_ID,
                derived_from=(certificate_evidence_id,),
            )
        return {
            "already_complete": False,
            "accepted": [row.to_dict() for row in accepted],
            "exclusions": [row.to_dict() for row in exclusions],
            "cursor": next_cursor.to_dict(),
            "pool": final_pool.to_dict(),
            "completeness_certificate": certificate_doc,
            "cursor_evidence_id": cursor_evidence_id,
            "completeness_certificate_evidence_id": certificate_evidence_id,
            "trace_digest": step["trace_digest"],
        }

    def enumerate_complete_solution_pool(
        self,
        model: OptimizationModel,
        *,
        lineage: Mapping[str, Any] | None = None,
        max_states_per_step: int = 1_000,
        max_total_states: int = 100_000,
        max_steps: int = 100_000,
    ) -> dict[str, Any]:
        started = self.start_solution_pool(
            model,
            mode="COMPLETE_FINITE_ENUMERATION",
            lineage=lineage,
            max_total_states=max_total_states,
        )
        pool_id = started["pool"]["pool_id"]
        for _ in range(int(max_steps)):
            current = self.solution_pool_report(pool_id)["pool"]
            if current["completeness_status"] == "COMPLETE":
                return self.solution_pool_report(pool_id)
            self.advance_solution_pool(
                pool_id,
                model,
                max_states_per_step=max_states_per_step,
                max_total_states=max_total_states,
            )
        raise RuntimeError("complete enumeration did not terminate within max_steps")
