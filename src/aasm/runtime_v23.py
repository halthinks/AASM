from __future__ import annotations

from copy import deepcopy
from inspect import signature
from typing import Any

from .calculus import (
    FairnessPolicy,
    assert_calculus_invariants,
    audit_fairness,
    candidate_exposes_overdue,
    decision_descendants,
    decision_values,
    normalize_calculus_state,
    reevaluate_locks,
    violated_hard_constraints,
)
from .decision_backends import (
    BackendBudget,
    BackendDiagnostic,
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

    def _validate_calculus_state_for_commit(self, state: dict[str, Any]) -> dict[str, Any]:
        """Validate a staged calculus before any durable write.

        Later runtime layers extend this hook with additional invariants. That
        keeps atomic multi-object commits on the same validation boundary as
        the inherited single-calculus commit path.
        """

        normalized = normalize_calculus_state(state)
        assert_calculus_invariants(normalized)
        return normalized

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

    @staticmethod
    def _invoke_batch_backend(backend: Any, request, budget, continuation):
        method = backend.propose_batch
        parameters = signature(method).parameters
        kwargs: dict[str, Any] = {}
        if "budget" in parameters:
            kwargs["budget"] = budget
        if "continuation" in parameters:
            kwargs["continuation"] = continuation
        return method(request, **kwargs)

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
            batch = self._invoke_batch_backend(backend, request, budget, continuation)
        else:
            raw = backend.propose(request)
            if isinstance(raw, CandidateModel):
                candidate = raw
                batch = CandidateBatch(
                    request_id=candidate.candidate_id,
                    backend_id=backend_id,
                    backend_version=str(getattr(backend, "backend_version", "0")),
                    candidates=[candidate],
                    exhausted=True,
                )
            elif isinstance(raw, dict) and "assignments" in raw:
                candidate = CandidateModel.from_dict(raw)
                batch = CandidateBatch(
                    request_id=candidate.candidate_id,
                    backend_id=backend_id,
                    backend_version=str(getattr(backend, "backend_version", "0")),
                    candidates=[candidate],
                    exhausted=True,
                )
            else:
                request_id = "request_" + self.snapshot.canonical_hash()[:16]
                batch = CandidateBatch(
                    request_id=request_id,
                    backend_id=backend_id,
                    backend_version=str(getattr(backend, "backend_version", "0")),
                    candidates=[],
                    exhausted=False,
                    diagnostics=[BackendDiagnostic(
                        "INPUT_REQUIRED",
                        "backend requires an external response before it can produce a candidate",
                        "INFO",
                        {"request_packet": deepcopy(raw)},
                    )],
                    certificate={"request_packet": deepcopy(raw)},
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
            "operation": "CANDIDATE_BATCH_GENERATED",
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

    def _stage_candidate_activation(
        self,
        calculus: dict[str, Any],
        assignments: dict[str, str],
        *,
        sequence: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Apply a complete candidate to an isolated calculus copy.

        Nothing is persisted from this method. Any failed precondition or
        invariant abandons the staged copy, which prevents partial candidate
        activation from leaking into durable machine state.
        """

        staged, initial_fairness = audit_fairness(normalize_calculus_state(calculus))
        decisions = staged["decisions"]
        previous_values = decision_values(staged)
        target_ids = set(assignments.values())

        for subject, decision_id in sorted(assignments.items()):
            decision = decisions.get(decision_id)
            if decision is None:
                raise KeyError(decision_id)
            if decision.get("subject") != subject:
                raise ValueError(
                    f"candidate subject {subject} does not match decision {decision_id} subject {decision.get('subject')}"
                )
            if decision.get("status") not in {"PROPOSED", "SUSPENDED", "ACTIVE"}:
                raise ValueError(
                    f"decision {decision_id} cannot activate from {decision.get('status')}"
                )
            inactive_parents = sorted(
                parent_id
                for parent_id in decision.get("parent_ids", [])
                if parent_id not in target_ids
                and decisions.get(parent_id, {}).get("status") != "ACTIVE"
            )
            if inactive_parents:
                raise ValueError(f"decision parents are not active: {inactive_parents}")
            inactive_antecedents = sorted(
                constraint_id
                for constraint_id in decision.get("antecedent_constraint_ids", [])
                if staged["constraints"].get(constraint_id, {}).get("status") not in {"ACTIVE", "SOFT"}
            )
            if inactive_antecedents:
                raise ValueError(
                    f"decision antecedent constraints are inactive: {inactive_antecedents}"
                )

        suspended_dependents: set[str] = set()
        superseded_decisions: set[str] = set()
        for subject, decision_id in sorted(assignments.items()):
            current_id = staged["active_model"].get(subject)
            if not current_id or current_id == decision_id:
                continue
            current = decisions[current_id]
            if current.get("pinned"):
                raise ValueError(f"pinned decision cannot be superseded: {current_id}")
            current["status"] = "SUPERSEDED"
            current["superseded_by"] = decision_id
            superseded_decisions.add(current_id)
            descendants = decision_descendants(staged, current_id) - {current_id}
            for dependent_id in sorted(descendants):
                dependent = decisions.get(dependent_id)
                if dependent is not None and dependent.get("status") == "ACTIVE":
                    dependent["status"] = "SUSPENDED"
                    suspended_dependents.add(dependent_id)
            removed = suspended_dependents | {current_id}
            staged["active_model"] = {
                active_subject: active_id
                for active_subject, active_id in staged["active_model"].items()
                if active_id not in removed
            }

        ordered = sorted(
            assignments.items(),
            key=lambda item: (
                int(decisions[item[1]].get("level", 0)),
                str(item[0]),
                str(item[1]),
            ),
        )
        for subject, decision_id in ordered:
            decision = decisions[decision_id]
            if staged["active_model"].get(subject) == decision_id and decision.get("status") == "ACTIVE":
                continue
            inactive_parents = sorted(
                parent_id
                for parent_id in decision.get("parent_ids", [])
                if decisions.get(parent_id, {}).get("status") != "ACTIVE"
            )
            if inactive_parents:
                raise ValueError(
                    f"candidate activation order left decision parents inactive: {inactive_parents}"
                )
            decision["status"] = "ACTIVE"
            decision["activated_sequence"] = sequence
            staged["active_model"][subject] = decision_id
            suspended_dependents.discard(decision_id)

        values = decision_values(staged)
        violations = violated_hard_constraints(staged, values)
        if violations:
            raise ValueError(f"candidate model violates learned hard constraints: {violations}")
        policy = FairnessPolicy(**deepcopy(staged["fairness"]["policy"]))
        if (
            initial_fairness["overdue"]
            and policy.enforcement == "BLOCK_PLANNING"
            and not candidate_exposes_overdue(staged, values, previous_values=previous_values)
        ):
            raise ValueError(
                "fairness blocks model selection until overdue obligations are exposed or dispositioned: "
                f"{initial_fairness['overdue']}"
            )

        staged["epoch"] = int(staged.get("epoch", 0)) + 1
        staged, broken = reevaluate_locks(staged)
        staged, fairness = audit_fairness(staged)
        return staged, {
            "broken_lock_ids": broken,
            "suspended_dependent_decision_ids": sorted(suspended_dependents),
            "superseded_decision_ids": sorted(superseded_decisions),
            "fairness": fairness,
        }

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

        sequence = self._sequence() + 1
        staged_calculus, activation = self._stage_candidate_activation(
            self._begin_calculus(),
            report.normalized_assignments,
            sequence=sequence,
        )
        staged_calculus = self._validate_calculus_state_for_commit(staged_calculus)

        state = self._candidate_state()
        row = state["candidates"].get(candidate_id)
        if row is None or row.get("status") not in {"ADMISSIBLE", "SELECTED"}:
            raise ValueError("candidate lifecycle changed during activation")
        previous = state.get("activated_candidate_id")
        if previous and previous != candidate_id and previous in state["candidates"]:
            prior = state["candidates"][previous]
            if prior.get("status") == "ACTIVATED":
                prior["status"] = "SUPERSEDED"
                prior["superseded_sequence"] = sequence
        row["status"] = "ACTIVATED"
        row["activated_sequence"] = sequence
        row["validation"] = report.to_dict()
        row.setdefault("activation", {}).update(deepcopy(activation))
        state["selected_candidate_id"] = candidate_id
        state["activated_candidate_id"] = candidate_id
        state["backend_history"].append({
            "sequence": sequence,
            "operation": "CANDIDATE_ACTIVATED",
            "candidate_id": candidate_id,
            "assignment_ids": deepcopy(report.normalized_assignments),
        })

        self.patch_snapshot(
            {"calculus": staged_calculus, "candidate_state": state},
            reason,
        )
        return {
            "candidate": deepcopy(state["candidates"][candidate_id]),
            "active_model": deepcopy(staged_calculus["active_model"]),
            **deepcopy(activation),
        }
