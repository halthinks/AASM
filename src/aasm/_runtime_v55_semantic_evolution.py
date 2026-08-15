from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .semantic_evolution import (
    INITIAL_REVISION_RECORD,
    PROBLEM_DELTA_CONTRACT_ID,
    PROBLEM_REVISION_CONTRACT_ID,
    REVISION_TRANSITION_RECORD,
    SEMANTIC_EVOLUTION_DOCUMENT,
    SEMANTIC_EVOLUTION_RECORD_TYPE,
    TRUTH_IMPACT_APPLICATION_RECORD,
    ProblemDelta,
    ProblemRevision,
    project_semantic_evolution_evidence,
    semantic_evolution_contract,
    semantic_evolution_document,
    validate_revision_transition,
)
from .semantic_result import semantic_fingerprint


SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID = "aasm.semantic-evolution.runtime.v1"
SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_VERSION = "0.1.0"
SEMANTIC_EVOLUTION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_REVISION_AUTHORITIES = {"POLICY", "CONTROLLER"}


def semantic_evolution_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID,
        "contract_version": SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_VERSION,
        "stability": SEMANTIC_EVOLUTION_RUNTIME_STABILITY,
        "model_contract": semantic_evolution_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "transition_commit": "ONE_DURABLE_REVISION_TRANSITION_EVIDENCE_RECORD",
        "optimistic_concurrency": "EXISTING_MACHINE_VERSION_GUARD",
        "current_head": "RECONSTRUCTED_FROM_APPEND_ONLY_EVIDENCE",
        "truth_maintenance": "EXISTING_AASM_SEMANTIC_DEPENDENCY_RUNTIME",
        "truth_maintenance_recovery": "IDEMPOTENT_RESUME_FROM_PENDING_DELTA",
        "revision_commit_authority": "POLICY_OR_CONTROLLER",
        "revision_record_grants_truth": False,
        "parallel_revision_table": "NONE",
        "parallel_change_impact_graph": "NONE",
        "historical_evidence_mutation_on_revision_change": "NONE",
        "pending_impact_policy": "REVISION_DEPENDENT_USE_FAILS_CLOSED",
    }


class SemanticEvolutionRuntimeMixin:
    """Durable v0.55 problem-revision semantics over existing Evidence/events.

    This mixin intentionally stores no mutable current-revision side table. The
    revision graph, current heads, and pending truth-maintenance work are
    reconstructed from canonical Evidence. A revision transition is committed
    first as one guarded Evidence record; dependency truth maintenance then runs
    through the existing v0.38 machinery and is idempotently resumable after a
    crash.
    """

    def semantic_evolution_runtime_contract_report(self) -> dict[str, Any]:
        return semantic_evolution_runtime_contract()

    def _semantic_evolution_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_semantic_evolution_evidence(records)

    def _require_valid_semantic_evolution_projection(self) -> dict[str, Any]:
        projection = self._semantic_evolution_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable semantic-evolution projection: {projection['issues']}")
        return projection

    def _record_semantic_evolution_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str] = (),
        reason: str,
        expected_machine_version: int | None = None,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": str(object_id), "document": payload}
        evidence_id = f"semantic-evolution-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(SEMANTIC_EVOLUTION_RECORD_TYPE) != record_type or metadata.get(SEMANTIC_EVOLUTION_DOCUMENT) != payload:
                raise ValueError(f"semantic evolution Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._require_evidence_ids(tuple(derived_from))
        record = EvidenceRecord(
            kind="semantic_evolution",
            statement=semantic_evolution_document(payload),
            source=source,
            derived_from=lineage,
            metadata={
                SEMANTIC_EVOLUTION_RECORD_TYPE: record_type,
                "object_id": str(object_id),
                SEMANTIC_EVOLUTION_DOCUMENT: payload,
                "authority": "GOVERNANCE_EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        expected = self.snapshot.version if expected_machine_version is None else int(expected_machine_version)
        self.add_evidence_guarded(record, expected_machine_version=expected, reason=reason)
        return evidence_id

    @staticmethod
    def _require_revision_authority(authority_id: str, authority_class: str) -> None:
        if not str(authority_id).strip():
            raise ValueError("problem revision authority_id is required")
        if authority_class not in _REVISION_AUTHORITIES:
            raise PermissionError("problem revision commit requires POLICY or CONTROLLER authority")

    def register_initial_problem_revision(
        self,
        revision: ProblemRevision | Mapping[str, Any],
        *,
        authority_id: str,
        authority_class: str,
        evidence_ids: Sequence[str] = (),
        reason: str = "initial problem revision registered",
    ) -> dict[str, Any]:
        self._require_revision_authority(authority_id, authority_class)
        item = revision if isinstance(revision, ProblemRevision) else ProblemRevision.from_dict(revision)
        if item.parent_revision_ids:
            raise ValueError("initial problem revision cannot have parents")
        if item.created_from_delta_id:
            raise ValueError("initial problem revision cannot be created from a delta")
        projection = self._require_valid_semantic_evolution_projection()
        prior_for_problem = [
            row for row in projection["revisions"].values()
            if row["revision"]["problem_id"] == item.problem_id
        ]
        existing = projection["revisions"].get(item.revision_id)
        if existing is not None:
            if existing["revision"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"problem revision identity collision: {item.revision_id}")
            return {"revision": deepcopy(existing["revision"]), "evidence_id": existing["evidence_id"], "already_registered": True}
        if prior_for_problem:
            raise ValueError(f"problem already has a durable initial revision: {item.problem_id}")
        lineage = self._require_evidence_ids(tuple(evidence_ids))
        document = {
            "revision": item.to_dict(),
            "authority_id": str(authority_id),
            "authority_class": authority_class,
        }
        evidence_id = self._record_semantic_evolution_document(
            record_type=INITIAL_REVISION_RECORD,
            object_id=item.revision_id,
            document=document,
            source=PROBLEM_REVISION_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"revision": item.to_dict(), "evidence_id": evidence_id, "already_registered": False}

    def _pending_impact_for_problem(self, projection: Mapping[str, Any], problem_id: str) -> list[str]:
        pending = []
        for delta_id in projection.get("pending_impact_delta_ids", []):
            transition = projection["transitions"].get(delta_id)
            if transition and transition["target_revision"].get("problem_id") == problem_id:
                pending.append(delta_id)
        return sorted(pending)

    def commit_problem_revision_transition(
        self,
        delta: ProblemDelta | Mapping[str, Any],
        target_revision: ProblemRevision | Mapping[str, Any],
        *,
        authority_id: str,
        authority_class: str,
        evidence_ids: Sequence[str] = (),
        reason: str = "problem revision transition committed",
        apply_truth_maintenance: bool = True,
    ) -> dict[str, Any]:
        self._require_revision_authority(authority_id, authority_class)
        change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
        target = target_revision if isinstance(target_revision, ProblemRevision) else ProblemRevision.from_dict(target_revision)
        projection = self._require_valid_semantic_evolution_projection()
        try:
            base_row = projection["revisions"][change.base_revision_id]
        except KeyError:
            raise KeyError(f"unknown durable base problem revision: {change.base_revision_id}") from None
        base = ProblemRevision.from_dict(base_row["revision"])
        if self._pending_impact_for_problem(projection, base.problem_id):
            raise RuntimeError("problem has pending revision truth maintenance; resume it before another transition")
        heads = projection["heads_by_problem"].get(base.problem_id, [])
        if heads != [base.revision_id]:
            raise ValueError(f"base revision is not the single current durable head: {base.revision_id}; heads={heads}")
        if target.parent_revision_ids != (base.revision_id,):
            raise ValueError("v0.55 foundation transition requires exactly one parent equal to the current base revision")
        if target.created_from_delta_id != change.delta_id:
            raise ValueError("target revision created_from_delta_id must equal the exact ProblemDelta")
        validation = validate_revision_transition(base, change, target)
        if not validation["valid"]:
            raise ValueError(f"invalid problem revision transition: {validation['errors']}")
        if target.revision_id in projection["revisions"]:
            prior = projection["revisions"][target.revision_id]
            if prior["revision"]["fingerprint"] != target.fingerprint:
                raise ValueError(f"target problem revision identity collision: {target.revision_id}")
            existing_transition = projection["transitions"].get(change.delta_id)
            if existing_transition is None:
                raise ValueError("target revision already exists without the requested delta transition")
            result = {
                "base_revision": base.to_dict(),
                "delta": change.to_dict(),
                "target_revision": target.to_dict(),
                "transition_evidence_id": existing_transition["transition_evidence_id"],
                "already_committed": True,
            }
            if apply_truth_maintenance and change.truth_change_roots:
                result["truth_maintenance"] = self.resume_problem_revision_impacts(change.delta_id)
            return result

        lineage = self._require_evidence_ids(tuple(sorted(set([
            *map(str, evidence_ids),
            *change.evidence_ids,
            *change.invalidated_evidence_ids,
            *change.preserved_evidence_ids,
            str(base_row["evidence_id"]),
        ]))))
        document = {
            "base_revision_id": base.revision_id,
            "base_revision_fingerprint": base.fingerprint,
            "delta": change.to_dict(),
            "target_revision": target.to_dict(),
            "authority_id": str(authority_id),
            "authority_class": authority_class,
        }
        expected_machine_version = self.snapshot.version
        transition_evidence_id = self._record_semantic_evolution_document(
            record_type=REVISION_TRANSITION_RECORD,
            object_id=change.delta_id,
            document=document,
            source=PROBLEM_DELTA_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
            expected_machine_version=expected_machine_version,
        )
        result = {
            "base_revision": base.to_dict(),
            "delta": change.to_dict(),
            "target_revision": target.to_dict(),
            "transition_evidence_id": transition_evidence_id,
            "already_committed": False,
        }
        if apply_truth_maintenance and change.truth_change_roots:
            result["truth_maintenance"] = self.resume_problem_revision_impacts(change.delta_id)
        return result

    def resume_problem_revision_impacts(self, delta_id: str) -> dict[str, Any]:
        projection = self._require_valid_semantic_evolution_projection()
        try:
            transition = projection["transitions"][delta_id]
        except KeyError:
            raise KeyError(delta_id) from None
        change = ProblemDelta.from_dict(transition["delta"])
        existing = projection["impact_applications"].get(delta_id)
        if existing is not None:
            return {
                "delta_id": delta_id,
                "already_applied": True,
                "application": deepcopy(existing["document"]),
                "application_evidence_id": existing["evidence_id"],
            }
        if not change.truth_change_roots:
            return {"delta_id": delta_id, "already_applied": True, "application": None, "application_evidence_id": None}

        authority_id = str(transition["authority_id"])
        authority_class = str(transition["authority_class"])
        transition_evidence_id = str(transition["transition_evidence_id"])
        applications = []
        generated_evidence_ids = []
        for root in change.truth_change_roots:
            impact_reason = f"problem delta {change.delta_id} changed {root.key}"
            result = self.apply_truth_change(
                root.node_type,
                root.node_id,
                reason=impact_reason,
                authority_id=authority_id,
                authority_class=authority_class,
                evidence_ids=[transition_evidence_id],
            )
            applications.append({
                "root": root.to_dict(),
                "plan_id": result["plan"]["plan_id"],
                "already_applied": bool(result["already_applied"]),
                "application_evidence_id": result.get("application_evidence_id"),
                "application": deepcopy(result.get("application")),
            })
            if result.get("application_evidence_id"):
                generated_evidence_ids.append(str(result["application_evidence_id"]))

        document = {
            "delta_id": change.delta_id,
            "transition_evidence_id": transition_evidence_id,
            "truth_change_roots": [row.to_dict() for row in change.truth_change_roots],
            "applications": applications,
            "authority_id": authority_id,
            "authority_class": authority_class,
            "handler_execution": "NONE",
        }
        application_evidence_id = self._record_semantic_evolution_document(
            record_type=TRUTH_IMPACT_APPLICATION_RECORD,
            object_id=change.delta_id,
            document=document,
            source=PROBLEM_DELTA_CONTRACT_ID,
            derived_from=[transition_evidence_id, *generated_evidence_ids],
            reason=f"problem revision truth maintenance completed: {change.delta_id}",
        )
        return {
            "delta_id": delta_id,
            "already_applied": False,
            "application": document,
            "application_evidence_id": application_evidence_id,
        }

    def semantic_evolution_report(self, problem_id: str | None = None) -> dict[str, Any]:
        projection = self._semantic_evolution_projection()
        if problem_id is None:
            return {
                "runtime_contract": semantic_evolution_runtime_contract(),
                **projection,
            }
        revisions = {
            revision_id: deepcopy(row)
            for revision_id, row in projection["revisions"].items()
            if row["revision"].get("problem_id") == problem_id
        }
        revision_ids = set(revisions)
        transitions = {
            delta_id: deepcopy(row)
            for delta_id, row in projection["transitions"].items()
            if row["target_revision"].get("problem_id") == problem_id
        }
        impacts = {
            delta_id: deepcopy(row)
            for delta_id, row in projection["impact_applications"].items()
            if delta_id in transitions
        }
        return {
            "runtime_contract": semantic_evolution_runtime_contract(),
            "contract": projection["contract"],
            "valid": projection["valid"],
            "issues": [
                deepcopy(row) for row in projection["issues"]
                if not row.get("evidence_id") or any(item.get("evidence_id") == row.get("evidence_id") for item in revisions.values())
            ],
            "problem_id": problem_id,
            "revisions": revisions,
            "transitions": transitions,
            "impact_applications": impacts,
            "heads": deepcopy(projection["heads_by_problem"].get(problem_id, [])),
            "pending_impact_delta_ids": [
                delta_id for delta_id in projection["pending_impact_delta_ids"] if delta_id in transitions
            ],
            "revision_count": len(revision_ids),
        }

    def require_usable_problem_revision(self, problem_id: str) -> dict[str, Any]:
        report = self.semantic_evolution_report(problem_id)
        if not report["valid"]:
            raise RuntimeError(f"problem revision history is invalid: {report['issues']}")
        if report["pending_impact_delta_ids"]:
            raise RuntimeError(
                f"problem revision has pending truth-maintenance work: {report['pending_impact_delta_ids']}"
            )
        if len(report["heads"]) != 1:
            raise RuntimeError(f"problem must have exactly one usable revision head: {report['heads']}")
        return deepcopy(report["revisions"][report["heads"][0]]["revision"])


__all__ = [
    "SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID",
    "SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_VERSION",
    "SEMANTIC_EVOLUTION_RUNTIME_STABILITY",
    "semantic_evolution_runtime_contract",
    "SemanticEvolutionRuntimeMixin",
]
