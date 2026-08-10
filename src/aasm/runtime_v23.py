from __future__ import annotations

from copy import deepcopy
from typing import Any

from .decision_backends import (
    BackendBudget,
    CandidateBatch,
    CandidateLifecycleRecord,
    DecisionBackendRegistry,
    default_backend_registry,
)
from .domain_adapters import CandidateModel
from .runtime_v22 import AASMEngine as V22Engine, default_profile_registry


class AASMEngine(V22Engine):
    """v0.23 runtime: solver-neutral candidate generation and lifecycle.

    Backends propose candidate models. The kernel records, validates, selects,
    and activates candidates under the same calculus and authority rules used
    by every other AASM operation.
    """

    def __init__(self, *args, backend_registry: DecisionBackendRegistry | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend_registry = backend_registry or default_backend_registry()

    @classmethod
    def _hydrate(cls, snapshot, events, store, authority=None, definition=None):
        self = super()._hydrate(snapshot, events, store, authority=authority, definition=definition)
        self.backend_registry = default_backend_registry()
        return self

    def _candidate_state(self) -> dict[str, Any]:
        return deepcopy(getattr(self.snapshot, "candidate_state", {}) or {
            "schema_version": 1,
            "requests": {},
            "batches": {},
            "candidates": {},
            "selected_candidate_id": None,
            "activated_candidate_id": None,
            "backend_history": [],
        })

    def backend_report(self) -> dict[str, Any]:
        state = self._candidate_state()
        return {
            "registered_backends": self.backend_registry.list(),
            "request_count": len(state["requests"]),
            "batch_count": len(state["batches"]),
            "candidate_count": len(state["candidates"]),
            "selected_candidate_id": state.get("selected_candidate_id"),
            "activated_candidate_id": state.get("activated_candidate_id"),
            "backend_history": deepcopy(state.get("backend_history", [])),
        }

    def generate_candidate_batch(
        self,
        backend_id: str = "aasm.finite-domain",
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
        reason: str = "decision backend generated candidate batch",
    ) -> dict[str, Any]:
        request = self.decision_request()
        backend = self.backend_registry.get(backend_id)
        if hasattr(backend, "propose_batch"):
            batch = backend.propose_batch(request, budget=budget, continuation=continuation)
        else:
            raw = backend.propose(request)
            candidate = raw if isinstance(raw, CandidateModel) else CandidateModel.from_dict(raw)
            batch = CandidateBatch(
                request_id=candidate.candidate_id,
                backend_id=backend_id,
                backend_version=str(getattr(backend, "backend_version", "0")),
                candidates=[candidate],
                exhausted=True,
            )

        state = self._candidate_state()
        request_payload = request.to_dict()
        state["requests"][batch.request_id] = request_payload
        state["batches"][batch.request_id + ":" + str(len(state["batches"]))] = batch.to_dict()
        sequence = self._sequence() + 1
        for candidate in batch.candidates:
            report = self.validate_candidate_model(candidate)
            lifecycle = CandidateLifecycleRecord(
                candidate=candidate.to_dict(),
                status="ADMISSIBLE" if report.valid else "REJECTED",
                rejection_reasons=list(report.errors),
                validation=report.to_dict(),
                proposed_sequence=sequence,
            )
            state["candidates"][candidate.candidate_id] = lifecycle.to_dict()
        state["backend_history"].append({
            "sequence": sequence,
            "backend_id": batch.backend_id,
            "backend_version": batch.backend_version,
            "request_id": batch.request_id,
            "candidate_ids": [candidate.candidate_id for candidate in batch.candidates],
            "exhausted": batch.exhausted,
            "continuation": batch.continuation,
            "usage": batch.usage.to_dict(),
        })
        self.patch_snapshot({"candidate_state": state}, reason)
        return batch.to_dict()

    def candidate_records(self, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = list(self._candidate_state()["candidates"].values())
        if status is not None:
            rows = [row for row in rows if row.get("status") == status]
        return deepcopy(sorted(rows, key=lambda row: row["candidate"]["candidate_id"]))

    def select_candidate(
        self,
        candidate_id: str,
        *,
        reason: str = "candidate selected for activation",
    ) -> dict[str, Any]:
        state = self._candidate_state()
        row = state["candidates"].get(candidate_id)
        if row is None:
            raise KeyError(candidate_id)
        candidate = CandidateModel.from_dict(row["candidate"])
        report = self.validate_candidate_model(candidate)
        if not report.valid:
            row["status"] = "REJECTED"
            row["rejection_reasons"] = list(report.errors)
            row["validation"] = report.to_dict()
            self.patch_snapshot({"candidate_state": state}, "stale candidate rejected during selection")
            raise ValueError("candidate is no longer admissible: " + "; ".join(report.errors))
        previous = state.get("selected_candidate_id")
        if previous and previous != candidate_id and previous in state["candidates"]:
            prior = state["candidates"][previous]
            if prior.get("status") == "SELECTED":
                prior["status"] = "SUPERSEDED"
                prior["superseded_sequence"] = self._sequence() + 1
        row["status"] = "SELECTED"
        row["selected_sequence"] = self._sequence() + 1
        row["validation"] = report.to_dict()
        state["selected_candidate_id"] = candidate_id
        self.patch_snapshot({"candidate_state": state}, reason)
        return deepcopy(row)

    def activate_candidate(
        self,
        candidate_id: str,
        *,
        reason: str = "candidate model activated",
    ) -> dict[str, Any]:
        state = self._candidate_state()
        row = state["candidates"].get(candidate_id)
        if row is None:
            raise KeyError(candidate_id)
        if row.get("status") not in {"ADMISSIBLE", "SELECTED"}:
            raise ValueError(f"candidate {candidate_id} cannot activate from {row.get('status')}")
        candidate = CandidateModel.from_dict(row["candidate"])
        report = self.validate_candidate_model(candidate)
        if not report.valid:
            row["status"] = "REJECTED"
            row["rejection_reasons"] = list(report.errors)
            row["validation"] = report.to_dict()
            self.patch_snapshot({"candidate_state": state}, "stale candidate rejected during activation")
            raise ValueError("candidate is no longer admissible: " + "; ".join(report.errors))

        calculus = self._begin_calculus()
        ordered_assignments = sorted(
            report.normalized_assignments.items(),
            key=lambda item: (
                int(calculus["decisions"].get(item[1], {}).get("level", 0)),
                str(item[0]),
                str(item[1]),
            ),
        )
        for subject, decision_id in ordered_assignments:
            calculus = self._begin_calculus()
            current_id = calculus["active_model"].get(subject)
            if current_id == decision_id:
                continue
            self.activate_decision(
                decision_id,
                supersede_decision_id=current_id,
                reason=f"candidate {candidate_id} activated decision {decision_id}",
            )

        state = self._candidate_state()
        row = state["candidates"][candidate_id]
        previous = state.get("activated_candidate_id")
        if previous and previous != candidate_id and previous in state["candidates"]:
            prior = state["candidates"][previous]
            if prior.get("status") == "ACTIVATED":
                prior["status"] = "SUPERSEDED"
                prior["superseded_sequence"] = self._sequence() + 1
        row["status"] = "ACTIVATED"
        row["activated_sequence"] = self._sequence() + 1
        row["validation"] = report.to_dict()
        state["selected_candidate_id"] = candidate_id
        state["activated_candidate_id"] = candidate_id
        self.patch_snapshot({"candidate_state": state}, reason)
        return {
            "candidate": deepcopy(row),
            "active_model": deepcopy(self._begin_calculus()["active_model"]),
        }
