from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Iterable, Mapping, Sequence

from .evidence import EvidenceRecord
from .refinement import (
    REFINEMENT_LOOP_CONTRACT_ID,
    REFINEMENT_PROPOSAL_CONTRACT_ID,
    RefinementApplication,
    RefinementLoopTermination,
    RefinementProposal,
    RefinementValidation,
    refinement_application_key,
    refinement_contract,
    validate_refinement_application,
    validate_refinement_delta,
    validate_refinement_validation,
)
from .scoped_authority import AuthorityRequest
from .semantic_evolution import (
    ProblemDelta,
    ProblemRevision,
    project_semantic_evolution_evidence,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint


REFINEMENT_RUNTIME_CONTRACT_ID = "aasm.refinement.runtime.v1"
REFINEMENT_RUNTIME_CONTRACT_VERSION = "0.1.0"
REFINEMENT_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

REFINEMENT_RECORD_TYPE = "aasm_refinement_record_type"
REFINEMENT_DOCUMENT = "document"

REFINEMENT_PROPOSAL_RECORD = "REFINEMENT_PROPOSAL"
REFINEMENT_VALIDATION_RECORD = "REFINEMENT_VALIDATION"
REFINEMENT_APPLICATION_RECORD = "REFINEMENT_APPLICATION"
REFINEMENT_TERMINATION_RECORD = "REFINEMENT_TERMINATION"
REFINEMENT_RECORD_TYPES = (
    REFINEMENT_PROPOSAL_RECORD,
    REFINEMENT_VALIDATION_RECORD,
    REFINEMENT_APPLICATION_RECORD,
    REFINEMENT_TERMINATION_RECORD,
)

REFINEMENT_APPLY_CAPABILITY = "problem.refinement.apply"

_SCOPED_AUTHORITY_RECORD_TYPE = "aasm_scoped_authority_record_type"
_AUTHORITY_DOCUMENT = "document"


def refinement_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": REFINEMENT_RUNTIME_CONTRACT_ID,
        "contract_version": REFINEMENT_RUNTIME_CONTRACT_VERSION,
        "stability": REFINEMENT_RUNTIME_STABILITY,
        "model_contract": refinement_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "proposal_record": REFINEMENT_PROPOSAL_RECORD,
        "validation_record": REFINEMENT_VALIDATION_RECORD,
        "application_record": REFINEMENT_APPLICATION_RECORD,
        "termination_record": REFINEMENT_TERMINATION_RECORD,
        "application_authority_capability": REFINEMENT_APPLY_CAPABILITY,
        "application_authority": "EXISTING_AASM_SCOPED_AUTHORITY_DECISION_REQUIRED",
        "revision_transition": "EXISTING_AASM_SEMANTIC_EVOLUTION_RUNTIME_ONLY",
        "truth_maintenance": "EXISTING_AASM_SEMANTIC_DEPENDENCY_RUNTIME_ONLY",
        "duplicate_application": "BASE_REVISION_PLUS_SEMANTIC_REFINEMENT_FINGERPRINT_FAIL_CLOSED",
        "crash_recovery": "REVISION_TRANSITION_AND_TRUTH_IMPACT_RECOVER_BEFORE_APPLICATION_RECORD",
        "producer_direct_application": "FORBIDDEN",
        "parallel_refinement_store": "NONE",
        "parallel_revision_system": "NONE",
        "parallel_authority_plane": "NONE",
        "parallel_truth_maintenance": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def refinement_document(value: Mapping[str, Any]) -> str:
    return canonical_semantic_json(deepcopy(dict(value)))


def _record_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(REFINEMENT_DOCUMENT)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        value = json.loads(statement)
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
    raise ValueError("refinement Evidence is missing its canonical document")


def _evidence_map(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def _authority_decisions(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    decisions: dict[str, dict[str, Any]] = {}
    for evidence_id, row in _evidence_map(records).items():
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_SCOPED_AUTHORITY_RECORD_TYPE) != "decision":
            continue
        document = metadata.get(_AUTHORITY_DOCUMENT)
        if not isinstance(document, Mapping):
            continue
        decisions[evidence_id] = deepcopy(dict(document))
    return decisions


def _structural_validation_errors(result: Mapping[str, Any]) -> list[str]:
    return [
        str(error)
        for error in result.get("errors", [])
        if not str(error).startswith("VALIDATION_RESULT_")
    ]


def project_refinement_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in records]
    evidence = _evidence_map(rows)
    authority_decisions = _authority_decisions(rows)
    semantic = project_semantic_evolution_evidence(rows)

    proposals: dict[str, dict[str, Any]] = {}
    validations: dict[str, dict[str, Any]] = {}
    applications: dict[str, dict[str, Any]] = {}
    terminations: dict[str, dict[str, Any]] = {}
    application_keys: dict[str, str] = {}
    issues: list[dict[str, Any]] = []

    if not semantic["valid"]:
        issues.append({
            "index": -1,
            "evidence_id": "",
            "record_type": "SEMANTIC_EVOLUTION",
            "error": f"canonical semantic-evolution history is invalid: {semantic['issues']}",
        })

    for index, raw in enumerate(rows):
        row = deepcopy(raw)
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(REFINEMENT_RECORD_TYPE)
        if record_type not in REFINEMENT_RECORD_TYPES:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _record_document(row)

            if record_type == REFINEMENT_PROPOSAL_RECORD:
                proposal = RefinementProposal.from_dict(document["proposal"])
                missing = sorted(set(proposal.trigger_evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"refinement proposal references missing trigger Evidence: {missing}")
                prior = proposals.get(proposal.proposal_id)
                if prior is not None and prior["proposal"]["fingerprint"] != proposal.fingerprint:
                    raise ValueError(f"refinement proposal identity collision: {proposal.proposal_id}")
                proposals[proposal.proposal_id] = {
                    "proposal": proposal.to_dict(),
                    "evidence_id": evidence_id,
                }

            elif record_type == REFINEMENT_VALIDATION_RECORD:
                validation = RefinementValidation.from_dict(document["validation"])
                proposal_row = proposals.get(validation.proposal_id)
                if proposal_row is None:
                    raise ValueError(f"refinement validation references unknown proposal: {validation.proposal_id}")
                proposal = RefinementProposal.from_dict(proposal_row["proposal"])
                result = validate_refinement_validation(proposal, validation)
                structural = _structural_validation_errors(result)
                if structural:
                    raise ValueError(f"refinement validation lineage is invalid: {structural}")
                missing = sorted(set(validation.supporting_evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"refinement validation references missing Evidence: {missing}")
                prior = validations.get(validation.validation_id)
                if prior is not None and prior["validation"]["fingerprint"] != validation.fingerprint:
                    raise ValueError(f"refinement validation identity collision: {validation.validation_id}")
                validations[validation.validation_id] = {
                    "validation": validation.to_dict(),
                    "evidence_id": evidence_id,
                    "application_eligible": bool(result["application_eligible"]),
                    "eligibility_errors": list(result["errors"]),
                }

            elif record_type == REFINEMENT_APPLICATION_RECORD:
                application = RefinementApplication.from_dict(document["application"])
                proposal_row = proposals.get(application.proposal_id)
                validation_row = validations.get(application.validation_id)
                if proposal_row is None:
                    raise ValueError(f"refinement application references unknown proposal: {application.proposal_id}")
                if validation_row is None:
                    raise ValueError(f"refinement application references unknown validation: {application.validation_id}")
                proposal = RefinementProposal.from_dict(proposal_row["proposal"])
                validation = RefinementValidation.from_dict(validation_row["validation"])

                transition = semantic["transitions"].get(application.delta_id)
                if transition is None:
                    raise ValueError(
                        f"refinement application references unknown canonical ProblemDelta transition: {application.delta_id}"
                    )
                delta = ProblemDelta.from_dict(transition["delta"])
                target = ProblemRevision.from_dict(transition["target_revision"])
                result = validate_refinement_application(proposal, validation, application, delta, target)
                if not result["valid"]:
                    raise ValueError(f"refinement application is invalid: {result['errors']}")
                if application.problem_transition_evidence_id != transition["transition_evidence_id"]:
                    raise ValueError("refinement application transition Evidence does not match canonical revision transition")

                authority = authority_decisions.get(application.scoped_authorization_evidence_id)
                if authority is None:
                    raise ValueError("refinement application references no durable scoped-authority decision")
                request = dict(authority.get("request") or {})
                decision = dict(authority.get("decision") or {})
                if decision.get("allowed") is not True:
                    raise PermissionError("refinement application scoped-authority decision is not ALLOW")
                expected_request = {
                    "principal_id": application.actor_principal_id,
                    "workspace_id": proposal.workspace_id,
                    "scope_id": proposal.scope_id,
                    "capability": REFINEMENT_APPLY_CAPABILITY,
                }
                for name, expected in expected_request.items():
                    if request.get(name) != expected:
                        raise PermissionError(f"refinement application scoped-authority {name} mismatch")

                truth_impact_evidence_id = ""
                if delta.truth_change_roots:
                    impact = semantic["impact_applications"].get(delta.delta_id)
                    if impact is None:
                        raise RuntimeError(
                            "refinement application exists before canonical truth-maintenance impact completed"
                        )
                    truth_impact_evidence_id = str(impact["evidence_id"])

                key = refinement_application_key(proposal)
                prior_application_id = application_keys.get(key)
                if prior_application_id is not None:
                    raise ValueError(
                        "DUPLICATE_SEMANTIC_REFINEMENT_APPLICATION: "
                        f"{key} already applied by {prior_application_id}"
                    )
                application_keys[key] = application.application_id
                applications[application.application_id] = {
                    "application": application.to_dict(),
                    "evidence_id": evidence_id,
                    "application_key": key,
                    "transition_evidence_id": transition["transition_evidence_id"],
                    "truth_impact_evidence_id": truth_impact_evidence_id,
                }

            else:
                termination = RefinementLoopTermination.from_dict(document["termination"])
                base_row = semantic["revisions"].get(termination.base_revision_id)
                head_row = semantic["revisions"].get(termination.head_revision_id)
                if base_row is None:
                    raise ValueError(
                        f"refinement termination references unknown base revision: {termination.base_revision_id}"
                    )
                if head_row is None:
                    raise ValueError(
                        f"refinement termination references unknown head revision: {termination.head_revision_id}"
                    )
                base = ProblemRevision.from_dict(base_row["revision"])
                head = ProblemRevision.from_dict(head_row["revision"])
                if base.problem_id != termination.problem_id or head.problem_id != termination.problem_id:
                    raise ValueError("refinement termination problem/revision lineage mismatch")
                missing = sorted(set(termination.evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"refinement termination references missing Evidence: {missing}")
                prior = terminations.get(termination.termination_id)
                if prior is not None and prior["termination"]["fingerprint"] != termination.fingerprint:
                    raise ValueError(f"refinement termination identity collision: {termination.termination_id}")
                terminations[termination.termination_id] = {
                    "termination": termination.to_dict(),
                    "evidence_id": evidence_id,
                }

        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })

    applied_proposals = {
        row["application"]["proposal_id"]
        for row in applications.values()
    }
    pending_proposal_ids = sorted(set(proposals) - applied_proposals)
    return {
        "contract": refinement_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "proposals": proposals,
        "validations": validations,
        "applications": applications,
        "terminations": terminations,
        "application_keys": application_keys,
        "pending_proposal_ids": pending_proposal_ids,
        "semantic_evolution": semantic,
    }


class RefinementRuntimeMixin:
    """Pre-admission S5.1 durable refinement loop over existing AASM planes.

    No mutable refinement side table is introduced. Proposal, validation,
    application, and termination records are append-only Evidence. Canonical
    problem mutation remains exclusively in SemanticEvolutionRuntimeMixin;
    authorization remains exclusively in ScopedAuthorityRuntimeMixin; and
    dependency invalidation remains exclusively in the existing truth-
    maintenance runtime.
    """

    def refinement_runtime_contract_report(self) -> dict[str, Any]:
        return refinement_runtime_contract()

    def _refinement_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_refinement_evidence(records)

    def _require_valid_refinement_projection(self) -> dict[str, Any]:
        projection = self._refinement_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable refinement projection: {projection['issues']}")
        return projection

    def _record_refinement_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str] = (),
        reason: str,
    ) -> str:
        if record_type not in REFINEMENT_RECORD_TYPES:
            raise ValueError(f"unsupported refinement Evidence record type: {record_type}")
        payload = deepcopy(dict(document))
        identity = {
            "record_type": record_type,
            "object_id": str(object_id),
            "document": payload,
        }
        evidence_id = f"refinement-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(REFINEMENT_RECORD_TYPE) != record_type
                or metadata.get(REFINEMENT_DOCUMENT) != payload
            ):
                raise ValueError(f"refinement Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._require_evidence_ids(tuple(derived_from))
        record = EvidenceRecord(
            kind="refinement",
            statement=refinement_document(payload),
            source=source,
            derived_from=list(lineage),
            metadata={
                REFINEMENT_RECORD_TYPE: record_type,
                "object_id": str(object_id),
                REFINEMENT_DOCUMENT: payload,
                "authority": "GOVERNANCE_EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        expected = self.snapshot.version
        self.add_evidence_guarded(
            record,
            expected_machine_version=expected,
            reason=reason,
        )
        return evidence_id

    def record_refinement_proposal(
        self,
        proposal: RefinementProposal | Mapping[str, Any],
        *,
        reason: str = "refinement proposal recorded",
    ) -> dict[str, Any]:
        item = proposal if isinstance(proposal, RefinementProposal) else RefinementProposal.from_dict(proposal)
        semantic = self._require_valid_semantic_evolution_projection()
        base_row = semantic["revisions"].get(item.base_revision_id)
        if base_row is None:
            raise KeyError(f"unknown durable refinement base revision: {item.base_revision_id}")
        base = ProblemRevision.from_dict(base_row["revision"])
        if base.fingerprint != item.base_revision_fingerprint:
            raise ValueError("refinement proposal base revision fingerprint does not match durable revision")
        heads = semantic["heads_by_problem"].get(base.problem_id, [])
        if heads != [base.revision_id]:
            raise ValueError(
                f"refinement proposal base is not the current durable head: {base.revision_id}; heads={heads}"
            )
        pending = self._pending_impact_for_problem(semantic, base.problem_id)
        if pending:
            raise RuntimeError(
                f"problem has pending revision truth maintenance before refinement proposal: {pending}"
            )
        existing = self._require_valid_refinement_projection()["proposals"].get(item.proposal_id)
        if existing is not None:
            if existing["proposal"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"refinement proposal identity collision: {item.proposal_id}")
            return {
                "proposal": deepcopy(existing["proposal"]),
                "evidence_id": existing["evidence_id"],
                "already_recorded": True,
            }
        lineage = self._require_evidence_ids(item.trigger_evidence_ids)
        evidence_id = self._record_refinement_document(
            record_type=REFINEMENT_PROPOSAL_RECORD,
            object_id=item.proposal_id,
            document={"proposal": item.to_dict()},
            source=REFINEMENT_PROPOSAL_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "proposal": item.to_dict(),
            "evidence_id": evidence_id,
            "already_recorded": False,
        }

    def record_refinement_validation(
        self,
        validation: RefinementValidation | Mapping[str, Any],
        *,
        reason: str = "refinement validation recorded",
    ) -> dict[str, Any]:
        item = validation if isinstance(validation, RefinementValidation) else RefinementValidation.from_dict(validation)
        projection = self._require_valid_refinement_projection()
        proposal_row = projection["proposals"].get(item.proposal_id)
        if proposal_row is None:
            raise KeyError(f"unknown durable refinement proposal: {item.proposal_id}")
        proposal = RefinementProposal.from_dict(proposal_row["proposal"])
        result = validate_refinement_validation(proposal, item)
        structural = _structural_validation_errors(result)
        if structural:
            if "INDEPENDENT_VALIDATOR_REQUIRED" in structural:
                raise PermissionError("independent refinement validation cannot be performed by the proposal producer")
            raise ValueError(f"refinement validation lineage mismatch: {structural}")
        if item.result == "VALID" and not result["application_eligible"]:
            raise PermissionError(f"refinement validation is not application eligible: {result['errors']}")
        existing = projection["validations"].get(item.validation_id)
        if existing is not None:
            if existing["validation"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"refinement validation identity collision: {item.validation_id}")
            return {
                "validation": deepcopy(existing["validation"]),
                "evidence_id": existing["evidence_id"],
                "application_eligible": bool(existing["application_eligible"]),
                "already_recorded": True,
            }
        evidence_lineage = self._require_evidence_ids(item.supporting_evidence_ids)
        evidence_id = self._record_refinement_document(
            record_type=REFINEMENT_VALIDATION_RECORD,
            object_id=item.validation_id,
            document={"validation": item.to_dict()},
            source=REFINEMENT_LOOP_CONTRACT_ID,
            derived_from=[proposal_row["evidence_id"], *evidence_lineage],
            reason=reason,
        )
        return {
            "validation": item.to_dict(),
            "evidence_id": evidence_id,
            "application_eligible": bool(result["application_eligible"]),
            "already_recorded": False,
        }

    def apply_refinement(
        self,
        *,
        proposal_id: str,
        validation_id: str,
        delta: ProblemDelta | Mapping[str, Any],
        target_revision: ProblemRevision | Mapping[str, Any],
        actor_principal_id: str,
        revision_authority_class: str,
        at_time: float = 0.0,
        reason: str = "governed refinement applied",
    ) -> dict[str, Any]:
        projection = self._require_valid_refinement_projection()
        proposal_row = projection["proposals"].get(str(proposal_id))
        validation_row = projection["validations"].get(str(validation_id))
        if proposal_row is None:
            raise KeyError(f"unknown durable refinement proposal: {proposal_id}")
        if validation_row is None:
            raise KeyError(f"unknown durable refinement validation: {validation_id}")
        proposal = RefinementProposal.from_dict(proposal_row["proposal"])
        validation = RefinementValidation.from_dict(validation_row["validation"])
        validation_result = validate_refinement_validation(proposal, validation)
        if not validation_result["application_eligible"]:
            raise PermissionError(
                f"refinement validation is not application eligible: {validation_result['errors']}"
            )
        actor = str(actor_principal_id).strip()
        if not actor:
            raise ValueError("refinement actor_principal_id is required")
        if actor == proposal.producer_principal_id:
            raise PermissionError("refinement producer/evaluator cannot directly apply its own delta")
        authority_class = str(revision_authority_class).strip().upper()
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("refinement revision commit requires existing POLICY or CONTROLLER authority")

        change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
        target = target_revision if isinstance(target_revision, ProblemRevision) else ProblemRevision.from_dict(target_revision)
        key = refinement_application_key(proposal)
        existing_application_id = projection["application_keys"].get(key)
        if existing_application_id is not None:
            prior = projection["applications"][existing_application_id]
            prior_app = RefinementApplication.from_dict(prior["application"])
            if prior_app.delta_id != change.delta_id or prior_app.target_revision_id != target.revision_id:
                raise ValueError(
                    "DUPLICATE_SEMANTIC_REFINEMENT_APPLICATION conflicts with a different delta/target"
                )
            return {
                **deepcopy(prior),
                "already_applied": True,
            }

        semantic = self._require_valid_semantic_evolution_projection()
        base_row = semantic["revisions"].get(proposal.base_revision_id)
        if base_row is None:
            raise KeyError(f"unknown durable refinement base revision: {proposal.base_revision_id}")
        base = ProblemRevision.from_dict(base_row["revision"])
        delta_result = validate_refinement_delta(proposal, base, change)
        if not delta_result["valid"]:
            raise ValueError(f"refinement ProblemDelta rejected: {delta_result['errors']}")

        existing_transition = semantic["transitions"].get(change.delta_id)
        if existing_transition is None:
            heads = semantic["heads_by_problem"].get(base.problem_id, [])
            if heads != [base.revision_id]:
                raise ValueError(
                    f"refinement base revision is stale: {base.revision_id}; heads={heads}"
                )

        authorization = self.authorize_scoped_request(
            AuthorityRequest(
                actor,
                proposal.workspace_id,
                proposal.scope_id,
                REFINEMENT_APPLY_CAPABILITY,
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
            ),
            derived_from=[proposal_row["evidence_id"], validation_row["evidence_id"]],
            reason="refinement application authority evaluated",
        )
        if not authorization["decision"]["allowed"]:
            raise PermissionError(
                f"refinement application authority denied: {authorization['decision']['reason']}"
            )

        if existing_transition is None:
            committed = self.commit_problem_revision_transition(
                change,
                target,
                authority_id=actor,
                authority_class=authority_class,
                evidence_ids=[
                    proposal_row["evidence_id"],
                    validation_row["evidence_id"],
                    authorization["evidence_id"],
                ],
                reason=reason,
                apply_truth_maintenance=True,
            )
        else:
            canonical_target = ProblemRevision.from_dict(existing_transition["target_revision"])
            canonical_delta = ProblemDelta.from_dict(existing_transition["delta"])
            if canonical_delta.fingerprint != change.fingerprint:
                raise ValueError("existing refinement transition delta fingerprint mismatch")
            if canonical_target.fingerprint != target.fingerprint:
                raise ValueError("existing refinement transition target fingerprint mismatch")
            truth_maintenance = None
            if change.truth_change_roots:
                truth_maintenance = self.resume_problem_revision_impacts(change.delta_id)
            committed = {
                "base_revision": base.to_dict(),
                "delta": change.to_dict(),
                "target_revision": target.to_dict(),
                "transition_evidence_id": existing_transition["transition_evidence_id"],
                "already_committed": True,
            }
            if truth_maintenance is not None:
                committed["truth_maintenance"] = truth_maintenance

        truth_impact_evidence_id = ""
        if change.truth_change_roots:
            truth = committed.get("truth_maintenance")
            if not isinstance(truth, Mapping) or not truth.get("application_evidence_id"):
                raise RuntimeError(
                    "refinement cannot be recorded as applied until canonical truth maintenance completes"
                )
            truth_impact_evidence_id = str(truth["application_evidence_id"])

        application = RefinementApplication(
            proposal_id=proposal.proposal_id,
            proposal_fingerprint=proposal.fingerprint,
            validation_id=validation.validation_id,
            validation_fingerprint=validation.fingerprint,
            semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
            base_revision_id=proposal.base_revision_id,
            base_revision_fingerprint=proposal.base_revision_fingerprint,
            delta_id=change.delta_id,
            delta_fingerprint=change.fingerprint,
            target_revision_id=target.revision_id,
            target_revision_fingerprint=target.fingerprint,
            producer_principal_id=proposal.producer_principal_id,
            actor_principal_id=actor,
            scoped_authorization_evidence_id=authorization["evidence_id"],
            problem_transition_evidence_id=str(committed["transition_evidence_id"]),
            metadata={
                "truth_impact_application_evidence_id": truth_impact_evidence_id,
                "revision_authority_class": authority_class,
            },
        )
        application_result = validate_refinement_application(
            proposal,
            validation,
            application,
            change,
            target,
        )
        if not application_result["valid"]:
            raise ValueError(f"refinement application record rejected: {application_result['errors']}")

        lineage = [
            proposal_row["evidence_id"],
            validation_row["evidence_id"],
            authorization["evidence_id"],
            str(committed["transition_evidence_id"]),
        ]
        if truth_impact_evidence_id:
            lineage.append(truth_impact_evidence_id)
        evidence_id = self._record_refinement_document(
            record_type=REFINEMENT_APPLICATION_RECORD,
            object_id=application.application_id,
            document={"application": application.to_dict()},
            source=REFINEMENT_LOOP_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "application": application.to_dict(),
            "evidence_id": evidence_id,
            "application_key": key,
            "transition": deepcopy(committed),
            "already_applied": False,
        }

    def record_refinement_termination(
        self,
        termination: RefinementLoopTermination | Mapping[str, Any],
        *,
        reason: str = "refinement loop termination recorded",
    ) -> dict[str, Any]:
        item = (
            termination
            if isinstance(termination, RefinementLoopTermination)
            else RefinementLoopTermination.from_dict(termination)
        )
        semantic = self._require_valid_semantic_evolution_projection()
        base_row = semantic["revisions"].get(item.base_revision_id)
        head_row = semantic["revisions"].get(item.head_revision_id)
        if base_row is None or head_row is None:
            raise ValueError("refinement termination requires durable base and head revisions")
        base = ProblemRevision.from_dict(base_row["revision"])
        head = ProblemRevision.from_dict(head_row["revision"])
        if base.problem_id != item.problem_id or head.problem_id != item.problem_id:
            raise ValueError("refinement termination problem/revision lineage mismatch")
        heads = semantic["heads_by_problem"].get(item.problem_id, [])
        if heads != [item.head_revision_id]:
            raise ValueError(
                f"refinement termination head is not the current durable head: {item.head_revision_id}; heads={heads}"
            )
        projection = self._require_valid_refinement_projection()
        existing = projection["terminations"].get(item.termination_id)
        if existing is not None:
            if existing["termination"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"refinement termination identity collision: {item.termination_id}")
            return {
                "termination": deepcopy(existing["termination"]),
                "evidence_id": existing["evidence_id"],
                "already_recorded": True,
            }
        lineage = self._require_evidence_ids(item.evidence_ids)
        evidence_id = self._record_refinement_document(
            record_type=REFINEMENT_TERMINATION_RECORD,
            object_id=item.termination_id,
            document={"termination": item.to_dict()},
            source=REFINEMENT_LOOP_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "termination": item.to_dict(),
            "evidence_id": evidence_id,
            "already_recorded": False,
        }

    def refinement_report(self) -> dict[str, Any]:
        return self._refinement_projection()


__all__ = [
    "REFINEMENT_RUNTIME_CONTRACT_ID",
    "REFINEMENT_RUNTIME_CONTRACT_VERSION",
    "REFINEMENT_RUNTIME_STABILITY",
    "REFINEMENT_RECORD_TYPE",
    "REFINEMENT_DOCUMENT",
    "REFINEMENT_PROPOSAL_RECORD",
    "REFINEMENT_VALIDATION_RECORD",
    "REFINEMENT_APPLICATION_RECORD",
    "REFINEMENT_TERMINATION_RECORD",
    "REFINEMENT_RECORD_TYPES",
    "REFINEMENT_APPLY_CAPABILITY",
    "refinement_runtime_contract",
    "refinement_document",
    "project_refinement_evidence",
    "RefinementRuntimeMixin",
]
