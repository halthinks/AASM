from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Iterable, Mapping, Sequence

from .calculus import normalize_calculus_state
from .evidence import EvidenceRecord
from .semantic_evolution import ProblemRevision, project_semantic_evolution_evidence
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .verification_planning import (
    VERIFICATION_DEBT_CONTRACT_ID,
    VERIFICATION_PLAN_CONTRACT_ID,
    VerificationEvidenceApplicability,
    VerificationPlan,
    validate_verification_plan,
)
from .verification_planning_assurance import assure_verification_planning_inputs
from .verification_planning_lifecycle import (
    project_verification_debt_current_assured,
    validate_verification_plan_current_applicability,
)


VERIFICATION_PLANNING_RUNTIME_CONTRACT_ID = "aasm.verification.planning.runtime.v1"
VERIFICATION_PLANNING_RUNTIME_CONTRACT_VERSION = "0.1.0"
VERIFICATION_PLANNING_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

VERIFICATION_PLANNING_RECORD_TYPE = "aasm_verification_planning_record_type"
VERIFICATION_PLANNING_DOCUMENT = "document"
VERIFICATION_PLAN_RECORD = "VERIFICATION_PLAN"
VERIFICATION_APPLICABILITY_RECORD = "VERIFICATION_EVIDENCE_APPLICABILITY"
VERIFICATION_PLANNING_RECORD_TYPES = (
    VERIFICATION_PLAN_RECORD,
    VERIFICATION_APPLICABILITY_RECORD,
)


def verification_planning_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": VERIFICATION_PLANNING_RUNTIME_CONTRACT_ID,
        "contract_version": VERIFICATION_PLANNING_RUNTIME_CONTRACT_VERSION,
        "stability": VERIFICATION_PLANNING_RUNTIME_STABILITY,
        "plan_contract": VERIFICATION_PLAN_CONTRACT_ID,
        "debt_contract": VERIFICATION_DEBT_CONTRACT_ID,
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "plan_record": VERIFICATION_PLAN_RECORD,
        "applicability_record": VERIFICATION_APPLICABILITY_RECORD,
        "debt_storage": "NONE_RECOMPUTED_PROJECTION_ONLY",
        "obligation_source": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "problem_revision_source": "EXISTING_AASM_SEMANTIC_EVOLUTION_ONLY",
        "plan_current_use": "CURRENT_SEMANTIC_APPLICABILITY_AND_SUPPORT_FRESHNESS_REQUIRED",
        "applicability_revision": "INVALIDATE_OLD_EVIDENCE_THEN_RECORD_NEW_ASSESSMENT",
        "verifier_execution": "NONE",
        "effect_dispatch": "NONE",
        "resource_reservation": "NONE",
        "fact_authority": "NONE",
        "obligation_mutation": "NONE",
        "problem_mutation": "NONE",
        "parallel_verification_store": "NONE",
        "parallel_debt_store": "NONE",
        "parallel_obligation_graph": "NONE",
        "parallel_evidence_store": "NONE",
        "parallel_authority_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def verification_planning_document(value: Mapping[str, Any]) -> str:
    return canonical_semantic_json(deepcopy(dict(value)))


def _record_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(VERIFICATION_PLANNING_DOCUMENT)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        value = json.loads(statement)
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
    raise ValueError("verification-planning Evidence is missing its canonical document")


def _evidence_map(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def verification_plan_support_evidence_ids(plan: VerificationPlan) -> tuple[str, ...]:
    values = set(plan.evidence_ids)
    for profile in plan.verifier_profiles:
        values.update(profile.supporting_evidence_ids)
        for reference in profile.references:
            values.update(reference.evidence_ids)
        values.update(profile.soundness_claim.evidence_ids)
        values.update(profile.completeness_claim.evidence_ids)
    return tuple(sorted(values))


def verification_applicability_key(plan_id: str, binding: VerificationEvidenceApplicability) -> str:
    return semantic_fingerprint(
        {
            "plan_id": str(plan_id),
            "evidence_id": binding.evidence_id,
            "obligation_id": binding.obligation_id,
        }
    )


def project_verification_planning_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in records]
    evidence = _evidence_map(rows)
    semantic = project_semantic_evolution_evidence(rows)
    plans: dict[str, dict[str, Any]] = {}
    applicability: dict[str, dict[str, Any]] = {}
    applicability_keys: dict[str, str] = {}
    issues: list[dict[str, Any]] = []

    if not semantic["valid"]:
        issues.append(
            {
                "index": -1,
                "evidence_id": "",
                "record_type": "SEMANTIC_EVOLUTION",
                "error": f"canonical semantic-evolution history is invalid: {semantic['issues']}",
            }
        )

    for index, row in enumerate(rows):
        if str(row.get("status", "active")) != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(VERIFICATION_PLANNING_RECORD_TYPE)
        if record_type not in VERIFICATION_PLANNING_RECORD_TYPES:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _record_document(row)
            if record_type == VERIFICATION_PLAN_RECORD:
                plan = VerificationPlan.from_dict(document["plan"])
                revision_row = semantic["revisions"].get(plan.problem_revision_id)
                if revision_row is None:
                    raise ValueError(
                        f"VERIFICATION_PLAN_PROBLEM_REVISION_MISSING: {plan.problem_revision_id}"
                    )
                revision = ProblemRevision.from_dict(revision_row["revision"])
                if revision.fingerprint != plan.problem_revision_fingerprint:
                    raise ValueError(
                        "VERIFICATION_PLAN_PROBLEM_REVISION_FINGERPRINT_MISMATCH: "
                        f"plan={plan.problem_revision_fingerprint} durable={revision.fingerprint}"
                    )
                missing = sorted(set(verification_plan_support_evidence_ids(plan)) - set(evidence))
                if missing:
                    raise ValueError(f"VERIFICATION_PLAN_SUPPORT_EVIDENCE_MISSING: {missing}")
                prior = plans.get(plan.plan_id)
                if prior is not None and prior["plan"]["fingerprint"] != plan.fingerprint:
                    raise ValueError(f"VERIFICATION_PLAN_IDENTITY_COLLISION: {plan.plan_id}")
                plans[plan.plan_id] = {
                    "plan": plan.to_dict(),
                    "evidence_id": evidence_id,
                    "support_evidence_ids": list(verification_plan_support_evidence_ids(plan)),
                }
            else:
                plan_id = str(document.get("plan_id") or "")
                plan_row = plans.get(plan_id)
                if plan_row is None:
                    raise ValueError(f"VERIFICATION_APPLICABILITY_UNKNOWN_PLAN: {plan_id}")
                plan = VerificationPlan.from_dict(plan_row["plan"])
                binding = VerificationEvidenceApplicability.from_dict(document["applicability"])
                if (
                    binding.problem_revision_id != plan.problem_revision_id
                    or binding.problem_revision_fingerprint != plan.problem_revision_fingerprint
                ):
                    raise ValueError(
                        f"VERIFICATION_APPLICABILITY_PLAN_REVISION_MISMATCH: {binding.applicability_id}"
                    )
                requirements = {row.obligation_id: row for row in plan.requirements}
                requirement = requirements.get(binding.obligation_id)
                if requirement is None:
                    raise ValueError(
                        f"VERIFICATION_APPLICABILITY_NON_PLAN_OBLIGATION: {binding.obligation_id}"
                    )
                if binding.obligation_semantic_fingerprint != requirement.obligation_semantic_fingerprint:
                    raise ValueError(
                        f"VERIFICATION_APPLICABILITY_OBLIGATION_FINGERPRINT_MISMATCH: {binding.obligation_id}"
                    )
                actual = evidence.get(binding.evidence_id)
                if actual is None:
                    raise ValueError(
                        f"VERIFICATION_APPLICABILITY_EVIDENCE_MISSING: {binding.evidence_id}"
                    )
                if str(actual.get("kind") or "") != binding.evidence_type:
                    raise ValueError(
                        "VERIFICATION_APPLICABILITY_EVIDENCE_TYPE_MISMATCH: "
                        f"declared={binding.evidence_type} actual={actual.get('kind', '')}"
                    )
                missing_assessment = sorted(set(binding.assessment_evidence_ids) - set(evidence))
                if missing_assessment:
                    raise ValueError(
                        f"VERIFICATION_APPLICABILITY_ASSESSMENT_EVIDENCE_MISSING: {missing_assessment}"
                    )
                if binding.status == "APPLICABLE" and not binding.assessment_evidence_ids:
                    raise ValueError(
                        "VERIFICATION_APPLICABILITY_ASSESSMENT_EVIDENCE_REQUIRED"
                    )
                if binding.verifier_profile_id:
                    profiles = {row.profile_id: row for row in plan.verifier_profiles}
                    profile = profiles.get(binding.verifier_profile_id)
                    if profile is None or profile.fingerprint != binding.verifier_profile_fingerprint:
                        raise ValueError(
                            f"VERIFICATION_APPLICABILITY_PROFILE_MISMATCH: {binding.applicability_id}"
                        )
                key = verification_applicability_key(plan_id, binding)
                prior_id = applicability_keys.get(key)
                if prior_id is not None and prior_id != binding.applicability_id:
                    raise ValueError(
                        "VERIFICATION_APPLICABILITY_ACTIVE_KEY_CONFLICT: "
                        f"{key} already bound by {prior_id}"
                    )
                applicability_keys[key] = binding.applicability_id
                applicability[binding.applicability_id] = {
                    "plan_id": plan_id,
                    "applicability": binding.to_dict(),
                    "evidence_id": evidence_id,
                    "applicability_key": key,
                }
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    return {
        "contract": verification_planning_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "plans": plans,
        "applicability": applicability,
        "applicability_keys": applicability_keys,
        "semantic_evolution": semantic,
    }


class VerificationPlanningRuntimeMixin:
    """Durable proposal/history S5.3 runtime over existing AASM Evidence.

    Verification debt remains recomputed. This mixin introduces neither a debt
    table nor a verifier executor.
    """

    def verification_planning_runtime_contract_report(self) -> dict[str, Any]:
        return verification_planning_runtime_contract()

    def _verification_planning_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_verification_planning_evidence(records)

    def _require_valid_verification_planning_projection(self) -> dict[str, Any]:
        projection = self._verification_planning_projection()
        if not projection["valid"]:
            raise RuntimeError(
                f"invalid durable verification-planning projection: {projection['issues']}"
            )
        return projection

    def _record_verification_planning_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        if record_type not in VERIFICATION_PLANNING_RECORD_TYPES:
            raise ValueError(f"unsupported verification-planning Evidence record type: {record_type}")
        payload = deepcopy(dict(document))
        identity = {
            "record_type": record_type,
            "object_id": object_id,
            "document": payload,
        }
        evidence_id = f"verification-planning-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(VERIFICATION_PLANNING_RECORD_TYPE) != record_type
                or metadata.get(VERIFICATION_PLANNING_DOCUMENT) != payload
            ):
                raise ValueError(f"verification-planning Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._require_evidence_ids(tuple(derived_from))
        record = EvidenceRecord(
            kind="verification_planning",
            statement=verification_planning_document(payload),
            source=source,
            derived_from=list(lineage),
            metadata={
                VERIFICATION_PLANNING_RECORD_TYPE: record_type,
                "object_id": object_id,
                VERIFICATION_PLANNING_DOCUMENT: payload,
                "authority": "PROPOSAL_OR_APPLICABILITY_EVIDENCE_ONLY",
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

    def record_verification_plan(
        self,
        plan: VerificationPlan | Mapping[str, Any],
        *,
        reason: str = "verification plan proposal recorded",
    ) -> dict[str, Any]:
        item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
        calculus_state = normalize_calculus_state(self._calculus())
        result = validate_verification_plan(calculus_state, item)
        if not result["valid"]:
            raise ValueError(f"verification plan does not match exact current planning state: {result['errors']}")

        semantic = self._require_valid_semantic_evolution_projection()
        revision_row = semantic["revisions"].get(item.problem_revision_id)
        if revision_row is None:
            raise KeyError(f"unknown verification-plan ProblemRevision: {item.problem_revision_id}")
        revision = ProblemRevision.from_dict(revision_row["revision"])
        if revision.fingerprint != item.problem_revision_fingerprint:
            raise ValueError("verification plan ProblemRevision fingerprint does not match durable revision")
        heads = semantic["heads_by_problem"].get(revision.problem_id, [])
        if heads != [revision.revision_id]:
            raise ValueError(
                f"STALE_VERIFICATION_PLAN_PROBLEM_REVISION: {revision.revision_id}; heads={heads}"
            )
        pending = self._pending_impact_for_problem(semantic, revision.problem_id)
        if pending:
            raise RuntimeError(
                f"verification plan cannot be recorded before revision truth maintenance completes: {pending}"
            )

        records = self.snapshot.evidence.get("records", [])
        assurance = assure_verification_planning_inputs(records, item, ())
        if not assurance["plan_support_valid"]:
            raise PermissionError(
                "STALE_OR_MISSING_VERIFICATION_PLAN_SUPPORT_REPLAN_REQUIRED: "
                + str(assurance["issues"])
            )

        projection = self._require_valid_verification_planning_projection()
        existing = projection["plans"].get(item.plan_id)
        if existing is not None:
            if existing["plan"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"verification plan identity collision: {item.plan_id}")
            return {
                "plan": deepcopy(existing["plan"]),
                "evidence_id": existing["evidence_id"],
                "already_recorded": True,
            }
        support = verification_plan_support_evidence_ids(item)
        evidence_id = self._record_verification_planning_document(
            record_type=VERIFICATION_PLAN_RECORD,
            object_id=item.plan_id,
            document={"plan": item.to_dict()},
            source=VERIFICATION_PLAN_CONTRACT_ID,
            derived_from=support,
            reason=reason,
        )
        return {
            "plan": item.to_dict(),
            "evidence_id": evidence_id,
            "already_recorded": False,
        }

    def record_verification_evidence_applicability(
        self,
        *,
        plan_id: str,
        applicability: VerificationEvidenceApplicability | Mapping[str, Any],
        reason: str = "verification evidence applicability recorded",
    ) -> dict[str, Any]:
        projection = self._require_valid_verification_planning_projection()
        plan_row = projection["plans"].get(str(plan_id))
        if plan_row is None:
            raise KeyError(f"unknown durable verification plan: {plan_id}")
        plan = VerificationPlan.from_dict(plan_row["plan"])
        binding = (
            applicability
            if isinstance(applicability, VerificationEvidenceApplicability)
            else VerificationEvidenceApplicability.from_dict(applicability)
        )
        lifecycle = validate_verification_plan_current_applicability(self._calculus(), plan)
        if not lifecycle["valid"]:
            raise PermissionError(
                "VERIFICATION_PLAN_CURRENT_SEMANTIC_DRIFT_REPLAN_REQUIRED: "
                + str(lifecycle["errors"])
            )
        if (
            binding.problem_revision_id != plan.problem_revision_id
            or binding.problem_revision_fingerprint != plan.problem_revision_fingerprint
        ):
            raise ValueError("verification applicability does not match exact plan ProblemRevision")
        requirements = {row.obligation_id: row for row in plan.requirements}
        requirement = requirements.get(binding.obligation_id)
        if requirement is None or binding.obligation_semantic_fingerprint != requirement.obligation_semantic_fingerprint:
            raise ValueError("verification applicability does not match a canonical plan requirement")

        records = self.snapshot.evidence.get("records", [])
        assurance = assure_verification_planning_inputs(records, plan, (binding,))
        if not assurance["plan_support_valid"]:
            raise PermissionError(
                "STALE_OR_MISSING_VERIFICATION_PLAN_SUPPORT_REPLAN_REQUIRED: "
                + str(assurance["issues"])
            )
        sanitized = VerificationEvidenceApplicability.from_dict(
            assurance["sanitized_applicability"][0]
        )
        if sanitized.fingerprint != binding.fingerprint:
            raise PermissionError(
                "VERIFICATION_APPLICABILITY_ASSURANCE_REJECTED: "
                + str(assurance["issues"])
            )

        key = verification_applicability_key(plan.plan_id, binding)
        prior_id = projection["applicability_keys"].get(key)
        if prior_id is not None:
            prior = projection["applicability"][prior_id]
            prior_binding = VerificationEvidenceApplicability.from_dict(prior["applicability"])
            if prior_binding.fingerprint != binding.fingerprint:
                raise ValueError(
                    "VERIFICATION_APPLICABILITY_ACTIVE_KEY_CONFLICT: invalidate the prior applicability Evidence before recording a replacement"
                )
            return {
                "plan_id": plan.plan_id,
                "applicability": prior_binding.to_dict(),
                "evidence_id": prior["evidence_id"],
                "applicability_key": key,
                "already_recorded": True,
            }

        lineage = {
            plan_row["evidence_id"],
            binding.evidence_id,
            *binding.assessment_evidence_ids,
        }
        if binding.verifier_profile_id:
            profile = next(row for row in plan.verifier_profiles if row.profile_id == binding.verifier_profile_id)
            lineage.update(profile.supporting_evidence_ids)
        evidence_id = self._record_verification_planning_document(
            record_type=VERIFICATION_APPLICABILITY_RECORD,
            object_id=binding.applicability_id,
            document={
                "plan_id": plan.plan_id,
                "applicability": binding.to_dict(),
            },
            source=VERIFICATION_DEBT_CONTRACT_ID,
            derived_from=tuple(sorted(lineage)),
            reason=reason,
        )
        return {
            "plan_id": plan.plan_id,
            "applicability": binding.to_dict(),
            "evidence_id": evidence_id,
            "applicability_key": key,
            "already_recorded": False,
        }

    def verification_debt_report(
        self,
        plan_id: str,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_verification_planning_projection()
        plan_row = projection["plans"].get(str(plan_id))
        if plan_row is None:
            raise KeyError(f"unknown durable verification plan: {plan_id}")
        plan = VerificationPlan.from_dict(plan_row["plan"])
        bindings = tuple(
            VerificationEvidenceApplicability.from_dict(row["applicability"])
            for row in projection["applicability"].values()
            if row["plan_id"] == plan.plan_id
        )
        records = self.snapshot.evidence.get("records", [])
        return project_verification_debt_current_assured(
            self._calculus(),
            records,
            plan,
            bindings,
            metadata=metadata,
        )

    def verification_planning_history_report(self) -> dict[str, Any]:
        return self._verification_planning_projection()


__all__ = [
    "VERIFICATION_PLANNING_RUNTIME_CONTRACT_ID",
    "VERIFICATION_PLANNING_RUNTIME_CONTRACT_VERSION",
    "VERIFICATION_PLANNING_RUNTIME_STABILITY",
    "VERIFICATION_PLANNING_RECORD_TYPE",
    "VERIFICATION_PLANNING_DOCUMENT",
    "VERIFICATION_PLAN_RECORD",
    "VERIFICATION_APPLICABILITY_RECORD",
    "VERIFICATION_PLANNING_RECORD_TYPES",
    "verification_planning_runtime_contract",
    "verification_planning_document",
    "verification_plan_support_evidence_ids",
    "verification_applicability_key",
    "project_verification_planning_evidence",
    "VerificationPlanningRuntimeMixin",
]
