from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .refinement import (
    RefinementLoopTermination,
    RefinementProposal,
    RefinementValidation,
    refinement_application_key,
)
from .refinement_runtime import RefinementRuntimeMixin, project_refinement_evidence
from .semantic_evolution import ProblemDelta, ProblemRevision


REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_ID = "aasm.refinement.runtime.assurance.v1"
REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_VERSION = "0.1.0"
REFINEMENT_RUNTIME_ASSURANCE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def refinement_runtime_assurance_contract() -> dict[str, Any]:
    return {
        "contract_id": REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_ID,
        "contract_version": REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_VERSION,
        "stability": REFINEMENT_RUNTIME_ASSURANCE_STABILITY,
        "base_runtime": "aasm.refinement.runtime.v1",
        "base_revision_binding": "CANONICAL_HISTORY_EXACT",
        "transition_authority_binding": "APPLICATION_ACTOR_MUST_MATCH_CANONICAL_TRANSITION_AUTHORITY",
        "truth_impact_binding": "EXACT_CANONICAL_IMPACT_EVIDENCE",
        "termination_revision_binding": "EXACT_CANONICAL_FINGERPRINTS",
        "validation_freshness": "ACTIVE_SUPPORT_REQUIRED_FOR_NEW_APPLICATION",
        "historical_replay": "INVALIDATED_SUPPORT_DOES_NOT_RETROACTIVELY_ERASE_COMMITTED_APPLICATION",
        "parallel_store": "NONE",
        "parallel_revision_system": "NONE",
        "parallel_authority_plane": "NONE",
        "parallel_truth_maintenance": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def _issue(
    issues: list[dict[str, Any]],
    *,
    record_type: str,
    object_id: str,
    evidence_id: str,
    code: str,
    detail: str,
) -> None:
    issues.append(
        {
            "index": -1,
            "record_type": record_type,
            "object_id": object_id,
            "evidence_id": evidence_id,
            "code": code,
            "error": f"{code}: {detail}",
        }
    )


def assure_refinement_projection(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Add cross-history assurance without creating another semantic state plane."""

    rows = [deepcopy(dict(row)) for row in records]
    projection = project_refinement_evidence(rows)
    semantic = projection["semantic_evolution"]
    issues = list(projection["issues"])

    for proposal_id, row in projection["proposals"].items():
        proposal = RefinementProposal.from_dict(row["proposal"])
        base_row = semantic["revisions"].get(proposal.base_revision_id)
        if base_row is None:
            _issue(
                issues,
                record_type="REFINEMENT_PROPOSAL",
                object_id=proposal_id,
                evidence_id=row["evidence_id"],
                code="PROPOSAL_BASE_REVISION_MISSING",
                detail=proposal.base_revision_id,
            )
            continue
        base = ProblemRevision.from_dict(base_row["revision"])
        if proposal.base_revision_fingerprint != base.fingerprint:
            _issue(
                issues,
                record_type="REFINEMENT_PROPOSAL",
                object_id=proposal_id,
                evidence_id=row["evidence_id"],
                code="PROPOSAL_BASE_REVISION_FINGERPRINT_MISMATCH",
                detail=f"proposal={proposal.base_revision_fingerprint} durable={base.fingerprint}",
            )
        if not set(proposal.dependency_fingerprints).issubset(set(base.dependency_fingerprints)):
            _issue(
                issues,
                record_type="REFINEMENT_PROPOSAL",
                object_id=proposal_id,
                evidence_id=row["evidence_id"],
                code="PROPOSAL_DEPENDENCY_NOT_APPLICABLE_TO_DURABLE_BASE",
                detail=str(sorted(set(proposal.dependency_fingerprints) - set(base.dependency_fingerprints))),
            )

    for application_id, row in projection["applications"].items():
        application = row["application"]
        delta_id = str(application["delta_id"])
        transition = semantic["transitions"].get(delta_id)
        if transition is None:
            continue
        if str(transition.get("authority_id") or "") != str(application["actor_principal_id"]):
            _issue(
                issues,
                record_type="REFINEMENT_APPLICATION",
                object_id=application_id,
                evidence_id=row["evidence_id"],
                code="APPLICATION_TRANSITION_AUTHORITY_PRINCIPAL_MISMATCH",
                detail=(
                    f"application={application['actor_principal_id']} "
                    f"transition={transition.get('authority_id', '')}"
                ),
            )
        authority_class = str(transition.get("authority_class") or "").upper()
        if authority_class not in {"POLICY", "CONTROLLER"}:
            _issue(
                issues,
                record_type="REFINEMENT_APPLICATION",
                object_id=application_id,
                evidence_id=row["evidence_id"],
                code="APPLICATION_TRANSITION_AUTHORITY_CLASS_INVALID",
                detail=authority_class,
            )

        delta = ProblemDelta.from_dict(transition["delta"])
        metadata = dict(application.get("metadata") or {})
        recorded_impact = str(metadata.get("truth_impact_application_evidence_id") or "")
        canonical_impact = semantic["impact_applications"].get(delta_id)
        if delta.truth_change_roots:
            canonical_id = str(canonical_impact["evidence_id"]) if canonical_impact is not None else ""
            if recorded_impact != canonical_id:
                _issue(
                    issues,
                    record_type="REFINEMENT_APPLICATION",
                    object_id=application_id,
                    evidence_id=row["evidence_id"],
                    code="APPLICATION_TRUTH_IMPACT_PROVENANCE_MISMATCH",
                    detail=f"application={recorded_impact} canonical={canonical_id}",
                )
        elif recorded_impact:
            _issue(
                issues,
                record_type="REFINEMENT_APPLICATION",
                object_id=application_id,
                evidence_id=row["evidence_id"],
                code="APPLICATION_SPURIOUS_TRUTH_IMPACT_PROVENANCE",
                detail=recorded_impact,
            )

    for termination_id, row in projection["terminations"].items():
        termination = RefinementLoopTermination.from_dict(row["termination"])
        base_row = semantic["revisions"].get(termination.base_revision_id)
        head_row = semantic["revisions"].get(termination.head_revision_id)
        if base_row is not None:
            base = ProblemRevision.from_dict(base_row["revision"])
            if termination.base_revision_fingerprint != base.fingerprint:
                _issue(
                    issues,
                    record_type="REFINEMENT_TERMINATION",
                    object_id=termination_id,
                    evidence_id=row["evidence_id"],
                    code="TERMINATION_BASE_REVISION_FINGERPRINT_MISMATCH",
                    detail=f"termination={termination.base_revision_fingerprint} durable={base.fingerprint}",
                )
        if head_row is not None:
            head = ProblemRevision.from_dict(head_row["revision"])
            if termination.head_revision_fingerprint != head.fingerprint:
                _issue(
                    issues,
                    record_type="REFINEMENT_TERMINATION",
                    object_id=termination_id,
                    evidence_id=row["evidence_id"],
                    code="TERMINATION_HEAD_REVISION_FINGERPRINT_MISMATCH",
                    detail=f"termination={termination.head_revision_fingerprint} durable={head.fingerprint}",
                )

    out = deepcopy(projection)
    out["assurance_contract"] = refinement_runtime_assurance_contract()
    out["issues"] = issues
    out["valid"] = not issues
    return out


class RefinementRuntimeAssuranceMixin(RefinementRuntimeMixin):
    """Cross-history fail-closed assurance for the S5.1 pre-admission runtime."""

    def refinement_runtime_assurance_contract_report(self) -> dict[str, Any]:
        return refinement_runtime_assurance_contract()

    def _refinement_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return assure_refinement_projection(records)

    def _require_active_validation_support(self, validation: RefinementValidation) -> None:
        by_id = {
            str(row.get("evidence_id") or ""): row
            for row in self.snapshot.evidence.get("records", [])
        }
        stale = sorted(
            evidence_id
            for evidence_id in validation.supporting_evidence_ids
            if evidence_id not in by_id or str(by_id[evidence_id].get("status", "active")) != "active"
        )
        if stale:
            raise PermissionError(
                "STALE_REFINEMENT_VALIDATION_EVIDENCE: " + ",".join(stale)
            )

    def record_refinement_validation(
        self,
        validation: RefinementValidation | Mapping[str, Any],
        *,
        reason: str = "refinement validation recorded",
    ) -> dict[str, Any]:
        item = validation if isinstance(validation, RefinementValidation) else RefinementValidation.from_dict(validation)
        if item.result == "VALID":
            self._require_active_validation_support(item)
        return super().record_refinement_validation(item, reason=reason)

    def apply_refinement(self, **kwargs: Any) -> dict[str, Any]:
        projection = self._require_valid_refinement_projection()
        proposal_id = str(kwargs.get("proposal_id") or "")
        validation_id = str(kwargs.get("validation_id") or "")
        proposal_row = projection["proposals"].get(proposal_id)
        validation_row = projection["validations"].get(validation_id)
        if proposal_row is None:
            raise KeyError(f"unknown durable refinement proposal: {proposal_id}")
        if validation_row is None:
            raise KeyError(f"unknown durable refinement validation: {validation_id}")
        proposal = RefinementProposal.from_dict(proposal_row["proposal"])
        key = refinement_application_key(proposal)
        if key in projection["application_keys"]:
            return super().apply_refinement(**kwargs)
        validation = RefinementValidation.from_dict(validation_row["validation"])
        self._require_active_validation_support(validation)
        return super().apply_refinement(**kwargs)


__all__ = [
    "REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_ID",
    "REFINEMENT_RUNTIME_ASSURANCE_CONTRACT_VERSION",
    "REFINEMENT_RUNTIME_ASSURANCE_STABILITY",
    "refinement_runtime_assurance_contract",
    "assure_refinement_projection",
    "RefinementRuntimeAssuranceMixin",
]
