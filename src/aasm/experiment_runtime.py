from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Iterable, Mapping, Sequence

from .evidence import EvidenceRecord
from .experiment import (
    EXPERIMENT_CONTRACT_ID,
    ExperimentSelectionCandidate,
    ExperimentSelectionProposal,
    ExperimentSpec,
    propose_experiment_selection,
)
from .semantic_evolution import ProblemRevision, project_semantic_evolution_evidence
from .semantic_result import canonical_semantic_json, semantic_fingerprint


EXPERIMENT_RUNTIME_CONTRACT_ID = "aasm.experiment.runtime.v1"
EXPERIMENT_RUNTIME_CONTRACT_VERSION = "0.1.0"
EXPERIMENT_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

EXPERIMENT_RECORD_TYPE = "aasm_experiment_record_type"
EXPERIMENT_DOCUMENT = "document"
EXPERIMENT_SPEC_RECORD = "EXPERIMENT_SPEC"
EXPERIMENT_SELECTION_RECORD = "EXPERIMENT_SELECTION_PROPOSAL"
EXPERIMENT_RECORD_TYPES = (EXPERIMENT_SPEC_RECORD, EXPERIMENT_SELECTION_RECORD)


def experiment_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EXPERIMENT_RUNTIME_CONTRACT_ID,
        "contract_version": EXPERIMENT_RUNTIME_CONTRACT_VERSION,
        "stability": EXPERIMENT_RUNTIME_STABILITY,
        "semantic_contract": EXPERIMENT_CONTRACT_ID,
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "problem_revision_source": "EXISTING_AASM_SEMANTIC_EVOLUTION_ONLY",
        "support_freshness": "ACTIVE_EVIDENCE_REQUIRED_FOR_NEW_SPEC_OR_SELECTION",
        "historical_replay": "LATER_INVALIDATION_DOES_NOT_ERASE_RECORDED_PROPOSALS",
        "selection_recheck": "DETERMINISTIC_RECOMPUTATION_FROM_RECORDED_CANDIDATES",
        "experiment_execution": "NONE",
        "effect_dispatch": "NONE",
        "resource_reservation": "NONE",
        "fact_authority": "NONE",
        "problem_mutation": "NONE",
        "parallel_experiment_store": "NONE",
        "parallel_revision_system": "NONE",
        "parallel_resource_plane": "NONE",
        "parallel_safety_plane": "NONE",
        "parallel_authority_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def experiment_document(value: Mapping[str, Any]) -> str:
    return canonical_semantic_json(deepcopy(dict(value)))


def _record_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(EXPERIMENT_DOCUMENT)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        value = json.loads(statement)
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
    raise ValueError("experiment Evidence is missing its canonical document")


def _evidence_map(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def experiment_support_evidence_ids(spec: ExperimentSpec) -> tuple[str, ...]:
    values = set(spec.evidence_ids)
    for hypothesis in spec.hypotheses:
        values.update(hypothesis.basis_evidence_ids)
    for binding in spec.context_bindings:
        values.update(binding.evidence_ids)
    return tuple(sorted(values))


def _issue(
    issues: list[dict[str, Any]],
    *,
    index: int,
    evidence_id: str,
    record_type: str,
    code: str,
    detail: str,
) -> None:
    issues.append(
        {
            "index": index,
            "evidence_id": evidence_id,
            "record_type": record_type,
            "code": code,
            "error": f"{code}: {detail}",
        }
    )


def project_experiment_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in records]
    evidence = _evidence_map(rows)
    semantic = project_semantic_evolution_evidence(rows)
    experiments: dict[str, dict[str, Any]] = {}
    selections: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    if not semantic["valid"]:
        _issue(
            issues,
            index=-1,
            evidence_id="",
            record_type="SEMANTIC_EVOLUTION",
            code="EXPERIMENT_SEMANTIC_HISTORY_INVALID",
            detail=str(semantic["issues"]),
        )

    for index, row in enumerate(rows):
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(EXPERIMENT_RECORD_TYPE)
        if record_type not in EXPERIMENT_RECORD_TYPES:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _record_document(row)
            if record_type == EXPERIMENT_SPEC_RECORD:
                spec = ExperimentSpec.from_dict(document["experiment"])
                base_row = semantic["revisions"].get(spec.problem_revision_id)
                if base_row is None:
                    raise ValueError(f"EXPERIMENT_PROBLEM_REVISION_MISSING: {spec.problem_revision_id}")
                base = ProblemRevision.from_dict(base_row["revision"])
                if base.fingerprint != spec.problem_revision_fingerprint:
                    raise ValueError(
                        "EXPERIMENT_PROBLEM_REVISION_FINGERPRINT_MISMATCH: "
                        f"experiment={spec.problem_revision_fingerprint} durable={base.fingerprint}"
                    )
                missing = sorted(set(experiment_support_evidence_ids(spec)) - set(evidence))
                if missing:
                    raise ValueError(f"EXPERIMENT_SUPPORT_EVIDENCE_MISSING: {missing}")
                prior = experiments.get(spec.experiment_id)
                if prior is not None and prior["experiment"]["fingerprint"] != spec.fingerprint:
                    raise ValueError(f"EXPERIMENT_IDENTITY_COLLISION: {spec.experiment_id}")
                experiments[spec.experiment_id] = {
                    "experiment": spec.to_dict(),
                    "evidence_id": evidence_id,
                    "support_evidence_ids": list(experiment_support_evidence_ids(spec)),
                }
            else:
                selection = ExperimentSelectionProposal.from_dict(document["selection"])
                missing_selection = sorted(set(selection.evidence_ids) - set(evidence))
                if missing_selection:
                    raise ValueError(f"EXPERIMENT_SELECTION_EVIDENCE_MISSING: {missing_selection}")
                for candidate in selection.candidates:
                    experiment_row = experiments.get(candidate.experiment_id)
                    if experiment_row is None:
                        raise ValueError(
                            f"EXPERIMENT_SELECTION_UNKNOWN_EXPERIMENT: {candidate.experiment_id}"
                        )
                    spec = ExperimentSpec.from_dict(experiment_row["experiment"])
                    if candidate.experiment_fingerprint != spec.fingerprint:
                        raise ValueError(
                            "EXPERIMENT_SELECTION_EXPERIMENT_FINGERPRINT_MISMATCH: "
                            f"{candidate.experiment_id}"
                        )
                    if (
                        candidate.problem_revision_id != spec.problem_revision_id
                        or candidate.problem_revision_fingerprint != spec.problem_revision_fingerprint
                    ):
                        raise ValueError(
                            "EXPERIMENT_SELECTION_EXPERIMENT_REVISION_MISMATCH: "
                            f"{candidate.experiment_id}"
                        )
                    missing_constraints = sorted(
                        set(candidate.constraint_assessment_evidence_ids) - set(evidence)
                    )
                    if missing_constraints:
                        raise ValueError(
                            "EXPERIMENT_SELECTION_CONSTRAINT_EVIDENCE_MISSING: "
                            f"{missing_constraints}"
                        )
                expected = propose_experiment_selection(
                    workspace_id=selection.workspace_id,
                    scope_id=selection.scope_id,
                    problem_revision_id=selection.problem_revision_id,
                    problem_revision_fingerprint=selection.problem_revision_fingerprint,
                    candidates=selection.candidates,
                    selection_policy_id=selection.selection_policy_id,
                    selection_policy_fingerprint=selection.selection_policy_fingerprint,
                    producer_principal_id=selection.producer_principal_id,
                    evidence_ids=selection.evidence_ids,
                    metadata=selection.metadata,
                )
                if expected.selected_candidate_id != selection.selected_candidate_id:
                    raise ValueError(
                        "EXPERIMENT_SELECTION_DETERMINISTIC_RECOMPUTATION_MISMATCH: "
                        f"recorded={selection.selected_candidate_id} expected={expected.selected_candidate_id}"
                    )
                prior = selections.get(selection.selection_id)
                if prior is not None and prior["selection"]["fingerprint"] != selection.fingerprint:
                    raise ValueError(f"EXPERIMENT_SELECTION_IDENTITY_COLLISION: {selection.selection_id}")
                selections[selection.selection_id] = {
                    "selection": selection.to_dict(),
                    "evidence_id": evidence_id,
                }
        except Exception as exc:
            _issue(
                issues,
                index=index,
                evidence_id=evidence_id,
                record_type=str(record_type),
                code="EXPERIMENT_RECORD_INVALID",
                detail=f"{type(exc).__name__}: {exc}",
            )

    selected_experiment_ids = sorted(
        {
            row["selection"]["selected_experiment_id"]
            for row in selections.values()
            if row["selection"].get("selected_experiment_id")
        }
    )
    return {
        "contract": experiment_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "experiments": experiments,
        "selections": selections,
        "selected_experiment_ids": selected_experiment_ids,
        "semantic_evolution": semantic,
    }


class ExperimentRuntimeMixin:
    """Durable proposal-only S5.2 experiment history over existing AASM Evidence."""

    def experiment_runtime_contract_report(self) -> dict[str, Any]:
        return experiment_runtime_contract()

    def _experiment_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_experiment_evidence(records)

    def _require_valid_experiment_projection(self) -> dict[str, Any]:
        projection = self._experiment_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable experiment projection: {projection['issues']}")
        return projection

    def _require_active_experiment_evidence(self, evidence_ids: Sequence[str]) -> tuple[str, ...]:
        required = tuple(sorted(set(map(str, evidence_ids))))
        by_id = {
            str(row.get("evidence_id") or ""): row
            for row in self.snapshot.evidence.get("records", [])
        }
        missing = sorted(evidence_id for evidence_id in required if evidence_id not in by_id)
        stale = sorted(
            evidence_id
            for evidence_id in required
            if evidence_id in by_id and str(by_id[evidence_id].get("status", "active")) != "active"
        )
        if missing:
            raise ValueError("EXPERIMENT_SUPPORT_EVIDENCE_MISSING: " + ",".join(missing))
        if stale:
            raise PermissionError("STALE_EXPERIMENT_SUPPORT_EVIDENCE: " + ",".join(stale))
        return required

    def _record_experiment_document(
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
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"experiment-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(EXPERIMENT_RECORD_TYPE) != record_type or metadata.get(EXPERIMENT_DOCUMENT) != payload:
                raise ValueError(f"experiment Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._require_active_experiment_evidence(derived_from)
        record = EvidenceRecord(
            kind="experiment",
            statement=experiment_document(payload),
            source=source,
            derived_from=list(lineage),
            metadata={
                EXPERIMENT_RECORD_TYPE: record_type,
                "object_id": object_id,
                EXPERIMENT_DOCUMENT: payload,
                "authority": "PROPOSAL_EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        expected = self.snapshot.version
        self.add_evidence_guarded(record, expected_machine_version=expected, reason=reason)
        return evidence_id

    def record_experiment_spec(
        self,
        experiment: ExperimentSpec | Mapping[str, Any],
        *,
        reason: str = "governed experiment proposal recorded",
    ) -> dict[str, Any]:
        spec = experiment if isinstance(experiment, ExperimentSpec) else ExperimentSpec.from_dict(experiment)
        semantic = self._require_valid_semantic_evolution_projection()
        revision_row = semantic["revisions"].get(spec.problem_revision_id)
        if revision_row is None:
            raise KeyError(f"unknown experiment ProblemRevision: {spec.problem_revision_id}")
        revision = ProblemRevision.from_dict(revision_row["revision"])
        if revision.fingerprint != spec.problem_revision_fingerprint:
            raise ValueError("experiment ProblemRevision fingerprint does not match durable revision")
        heads = semantic["heads_by_problem"].get(revision.problem_id, [])
        if heads != [revision.revision_id]:
            raise ValueError(
                f"STALE_EXPERIMENT_PROBLEM_REVISION: {revision.revision_id}; heads={heads}"
            )
        pending = self._pending_impact_for_problem(semantic, revision.problem_id)
        if pending:
            raise RuntimeError(
                f"experiment cannot be recorded before revision truth maintenance completes: {pending}"
            )
        support = self._require_active_experiment_evidence(experiment_support_evidence_ids(spec))
        projection = self._require_valid_experiment_projection()
        existing = projection["experiments"].get(spec.experiment_id)
        if existing is not None:
            if existing["experiment"]["fingerprint"] != spec.fingerprint:
                raise ValueError(f"experiment identity collision: {spec.experiment_id}")
            return {
                "experiment": deepcopy(existing["experiment"]),
                "evidence_id": existing["evidence_id"],
                "already_recorded": True,
            }
        evidence_id = self._record_experiment_document(
            record_type=EXPERIMENT_SPEC_RECORD,
            object_id=spec.experiment_id,
            document={"experiment": spec.to_dict()},
            source=EXPERIMENT_CONTRACT_ID,
            derived_from=support,
            reason=reason,
        )
        return {"experiment": spec.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def record_experiment_selection(
        self,
        selection: ExperimentSelectionProposal | Mapping[str, Any],
        *,
        reason: str = "governed experiment selection proposal recorded",
    ) -> dict[str, Any]:
        item = selection if isinstance(selection, ExperimentSelectionProposal) else ExperimentSelectionProposal.from_dict(selection)
        projection = self._require_valid_experiment_projection()
        semantic = self._require_valid_semantic_evolution_projection()
        revision_row = semantic["revisions"].get(item.problem_revision_id)
        if revision_row is None:
            raise KeyError(f"unknown experiment selection ProblemRevision: {item.problem_revision_id}")
        revision = ProblemRevision.from_dict(revision_row["revision"])
        if revision.fingerprint != item.problem_revision_fingerprint:
            raise ValueError("experiment selection ProblemRevision fingerprint does not match durable revision")
        heads = semantic["heads_by_problem"].get(revision.problem_id, [])
        if heads != [revision.revision_id]:
            raise ValueError(
                f"STALE_EXPERIMENT_SELECTION_REVISION: {revision.revision_id}; heads={heads}"
            )

        support = set(self._require_active_experiment_evidence(item.evidence_ids))
        for candidate in item.candidates:
            experiment_row = projection["experiments"].get(candidate.experiment_id)
            if experiment_row is None:
                raise KeyError(f"EXPERIMENT_SELECTION_UNKNOWN_EXPERIMENT: {candidate.experiment_id}")
            spec = ExperimentSpec.from_dict(experiment_row["experiment"])
            if candidate.experiment_fingerprint != spec.fingerprint:
                raise ValueError(
                    f"EXPERIMENT_SELECTION_EXPERIMENT_FINGERPRINT_MISMATCH: {candidate.experiment_id}"
                )
            if candidate.problem_revision_id != spec.problem_revision_id or candidate.problem_revision_fingerprint != spec.problem_revision_fingerprint:
                raise ValueError(
                    f"EXPERIMENT_SELECTION_EXPERIMENT_REVISION_MISMATCH: {candidate.experiment_id}"
                )
            support.update(self._require_active_experiment_evidence(candidate.constraint_assessment_evidence_ids))
            if candidate.eligible:
                support.update(self._require_active_experiment_evidence(experiment_support_evidence_ids(spec)))

        expected = propose_experiment_selection(
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            problem_revision_id=item.problem_revision_id,
            problem_revision_fingerprint=item.problem_revision_fingerprint,
            candidates=item.candidates,
            selection_policy_id=item.selection_policy_id,
            selection_policy_fingerprint=item.selection_policy_fingerprint,
            producer_principal_id=item.producer_principal_id,
            evidence_ids=item.evidence_ids,
            metadata=item.metadata,
        )
        if expected.selected_candidate_id != item.selected_candidate_id:
            raise ValueError(
                "EXPERIMENT_SELECTION_DETERMINISTIC_RECOMPUTATION_MISMATCH: "
                f"recorded={item.selected_candidate_id} expected={expected.selected_candidate_id}"
            )
        existing = projection["selections"].get(item.selection_id)
        if existing is not None:
            if existing["selection"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"experiment selection identity collision: {item.selection_id}")
            return {
                "selection": deepcopy(existing["selection"]),
                "evidence_id": existing["evidence_id"],
                "already_recorded": True,
            }
        evidence_id = self._record_experiment_document(
            record_type=EXPERIMENT_SELECTION_RECORD,
            object_id=item.selection_id,
            document={"selection": item.to_dict()},
            source=EXPERIMENT_CONTRACT_ID,
            derived_from=tuple(sorted(support)),
            reason=reason,
        )
        return {"selection": item.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def propose_and_record_experiment_selection(
        self,
        *,
        workspace_id: str,
        scope_id: str,
        problem_revision_id: str,
        problem_revision_fingerprint: str,
        candidates: Sequence[ExperimentSelectionCandidate | Mapping[str, Any]],
        selection_policy_id: str,
        selection_policy_fingerprint: str,
        producer_principal_id: str,
        evidence_ids: Sequence[str],
        metadata: Mapping[str, Any] | None = None,
        reason: str = "governed experiment selection proposal recorded",
    ) -> dict[str, Any]:
        selection = propose_experiment_selection(
            workspace_id=workspace_id,
            scope_id=scope_id,
            problem_revision_id=problem_revision_id,
            problem_revision_fingerprint=problem_revision_fingerprint,
            candidates=candidates,
            selection_policy_id=selection_policy_id,
            selection_policy_fingerprint=selection_policy_fingerprint,
            producer_principal_id=producer_principal_id,
            evidence_ids=evidence_ids,
            metadata=metadata,
        )
        return self.record_experiment_selection(selection, reason=reason)

    def experiment_report(self) -> dict[str, Any]:
        return self._experiment_projection()


__all__ = [
    "EXPERIMENT_RUNTIME_CONTRACT_ID",
    "EXPERIMENT_RUNTIME_CONTRACT_VERSION",
    "EXPERIMENT_RUNTIME_STABILITY",
    "EXPERIMENT_RECORD_TYPE",
    "EXPERIMENT_DOCUMENT",
    "EXPERIMENT_SPEC_RECORD",
    "EXPERIMENT_SELECTION_RECORD",
    "EXPERIMENT_RECORD_TYPES",
    "experiment_runtime_contract",
    "experiment_document",
    "experiment_support_evidence_ids",
    "project_experiment_evidence",
    "ExperimentRuntimeMixin",
]
