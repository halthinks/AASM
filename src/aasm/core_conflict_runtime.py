from __future__ import annotations

"""S5.5 enforcement for backend-independent conflict/core refinement."""

from typing import Iterable, Mapping, Any

from .core_conflict import CoreClaim, CoreMember, CoreProvenance, CoreRecheck, ConflictCore

CORE_CONFLICT_RUNTIME_CONTRACT_ID = "aasm.core-conflict.runtime.v1"
CORE_CONFLICT_RUNTIME_CONTRACT_VERSION = "0.1.0"
CORE_CONFLICT_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
CORE_CONFLICT_AUTHORITY_CEILING = {
    "solver_output_authority": "NONE",
    "core_claim_self_upgrade": "NONE",
    "learned_constraint_admission": "NONE",
    "knowledge_reuse": "S5.4_APPLICABILITY_REQUIRED",
    "effect_dispatch": "NONE",
    "problem_mutation": "NONE",
    "runtime_admission": "PRE_ADMISSION_ONLY",
    "public_admission": "PRE_ADMISSION_ONLY",
}


class CoreConflictRejected(ValueError):
    pass


def _reject(reason: str) -> None:
    raise CoreConflictRejected(reason)


def _same_problem(parent: ConflictCore, provenance: CoreProvenance) -> None:
    if provenance.problem_revision_id != parent.provenance.problem_revision_id:
        _reject("PROBLEM_REVISION_MISMATCH")
    if provenance.problem_semantic_fingerprint != parent.provenance.problem_semantic_fingerprint:
        _reject("PROBLEM_SEMANTIC_FINGERPRINT_MISMATCH")


def _subset(parent: ConflictCore, members: Iterable[CoreMember]) -> tuple[CoreMember, ...]:
    child = tuple(members)
    parent_ids = {m.normalized_reference_id for m in parent.members}
    if not child:
        _reject("EMPTY_CONFLICT_CORE")
    if any(m.normalized_reference_id not in parent_ids for m in child):
        _reject("CORE_REDUCTION_MAY_NOT_INTRODUCE_MEMBERS")
    parent_by_id = {m.normalized_reference_id: m for m in parent.members}
    if any(parent_by_id[m.normalized_reference_id].fingerprint != m.fingerprint for m in child):
        _reject("CORE_MEMBER_IDENTITY_DRIFT")
    return child


def capture_raw_core(*, provenance: CoreProvenance, members: Iterable[CoreMember], evidence_ids: tuple[str, ...], metadata: Mapping[str, Any] | None = None) -> ConflictCore:
    return ConflictCore(
        provenance=provenance,
        members=tuple(members),
        stage="RAW",
        claim=CoreClaim("BACKEND_REPORTED", True, evidence_ids),
        metadata=metadata or {},
    )


def normalize_core(*, raw: ConflictCore, members: Iterable[CoreMember], evidence_ids: tuple[str, ...], metadata: Mapping[str, Any] | None = None) -> ConflictCore:
    if raw.stage != "RAW":
        _reject("NORMALIZATION_REQUIRES_RAW_CORE")
    child = _subset(raw, members)
    return ConflictCore(
        provenance=raw.provenance,
        members=child,
        stage="NORMALIZED",
        claim=CoreClaim("CONFLICT_PRESERVING", False, ()),
        parent_core_fingerprint=raw.fingerprint,
        transformation_evidence_ids=evidence_ids,
        metadata=metadata or {},
    )


def reduce_core(
    *,
    parent: ConflictCore,
    members: Iterable[CoreMember],
    evidence_ids: tuple[str, ...],
    budget_exhausted: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> ConflictCore:
    if parent.stage not in {"NORMALIZED", "REDUCED", "RECHECKED"}:
        _reject("REDUCTION_REQUIRES_NORMALIZED_OR_LATER_CORE")
    child = _subset(parent, members)
    kind = "BUDGET_LIMITED_PARTIAL" if budget_exhausted else "CONFLICT_PRESERVING"
    return ConflictCore(
        provenance=parent.provenance,
        members=child,
        stage="REDUCED",
        claim=CoreClaim(
            claim_kind=kind,
            established=bool(budget_exhausted),
            evidence_ids=evidence_ids if budget_exhausted else (),
            budget_exhausted=bool(budget_exhausted),
        ),
        parent_core_fingerprint=parent.fingerprint,
        transformation_evidence_ids=evidence_ids,
        metadata=metadata or {},
    )


def _validate_full_recheck(core: ConflictCore, recheck: CoreRecheck, *, require_independent: bool) -> None:
    if recheck.source_core_fingerprint != core.fingerprint:
        _reject("RECHECK_CORE_FINGERPRINT_MISMATCH")
    if recheck.problem_semantic_fingerprint != core.provenance.problem_semantic_fingerprint:
        _reject("RECHECK_PROBLEM_FINGERPRINT_MISMATCH")
    if set(recheck.checked_member_ids) != {m.normalized_reference_id for m in core.members}:
        _reject("RECHECK_MEMBER_SET_MISMATCH")
    if require_independent and not recheck.independent_from_solver_run:
        _reject("INDEPENDENT_RECHECK_REQUIRED")


def certify_conflict_preserving(*, core: ConflictCore, recheck: CoreRecheck) -> ConflictCore:
    _validate_full_recheck(core, recheck, require_independent=False)
    if recheck.outcome != "CONFLICT":
        _reject("CONFLICT_NOT_REPRODUCED")
    return ConflictCore(
        provenance=core.provenance,
        members=core.members,
        stage="RECHECKED",
        claim=CoreClaim("CONFLICT_PRESERVING", True, recheck.evidence_ids, certificate={"recheck_fingerprint": recheck.fingerprint}),
        parent_core_fingerprint=core.fingerprint,
        transformation_evidence_ids=recheck.evidence_ids,
    )


def certify_irreducible(*, core: ConflictCore, full_recheck: CoreRecheck, removal_rechecks: Mapping[str, CoreRecheck]) -> ConflictCore:
    _validate_full_recheck(core, full_recheck, require_independent=True)
    if full_recheck.outcome != "CONFLICT":
        _reject("FULL_CORE_CONFLICT_NOT_REPRODUCED")
    member_ids = {m.normalized_reference_id for m in core.members}
    if set(removal_rechecks) != member_ids:
        _reject("IRREDUCIBILITY_REQUIRES_ONE_REMOVAL_RECHECK_PER_MEMBER")
    evidence = set(full_recheck.evidence_ids)
    for removed, check in removal_rechecks.items():
        if check.source_core_fingerprint != core.fingerprint or check.problem_semantic_fingerprint != core.provenance.problem_semantic_fingerprint:
            _reject("IRREDUCIBILITY_RECHECK_PROVENANCE_MISMATCH")
        expected = member_ids - {removed}
        if set(check.checked_member_ids) != expected:
            _reject("IRREDUCIBILITY_RECHECK_MEMBER_SET_MISMATCH")
        if not check.independent_from_solver_run:
            _reject("IRREDUCIBILITY_REQUIRES_INDEPENDENT_RECHECKS")
        if check.outcome != "SATISFIABLE":
            _reject("IRREDUCIBILITY_NOT_ESTABLISHED")
        evidence.update(check.evidence_ids)
    return ConflictCore(
        provenance=core.provenance,
        members=core.members,
        stage="RECHECKED",
        claim=CoreClaim("IRREDUCIBLE", True, tuple(sorted(evidence)), certificate={"full": full_recheck.fingerprint, "removals": {k: v.fingerprint for k, v in sorted(removal_rechecks.items())}}),
        parent_core_fingerprint=core.fingerprint,
        transformation_evidence_ids=tuple(sorted(evidence)),
    )


def certify_minimum_cardinality(*, core: ConflictCore, evidence_ids: tuple[str, ...], certificate: Mapping[str, Any]) -> ConflictCore:
    if not certificate or not certificate.get("exhaustive_smaller_cardinalities_checked"):
        _reject("MINIMUM_CARDINALITY_REQUIRES_EXPLICIT_EXHAUSTIVE_CERTIFICATE")
    if certificate.get("problem_semantic_fingerprint") != core.provenance.problem_semantic_fingerprint:
        _reject("MINIMUM_CARDINALITY_CERTIFICATE_FINGERPRINT_MISMATCH")
    return ConflictCore(
        provenance=core.provenance,
        members=core.members,
        stage="RECHECKED",
        claim=CoreClaim("MINIMUM_CARDINALITY", True, evidence_ids, certificate=certificate),
        parent_core_fingerprint=core.fingerprint,
        transformation_evidence_ids=evidence_ids,
    )


def certify_minimum_weight(*, core: ConflictCore, evidence_ids: tuple[str, ...], objective: Mapping[str, Any], certificate: Mapping[str, Any]) -> ConflictCore:
    if core.total_weight is None:
        _reject("MINIMUM_WEIGHT_REQUIRES_WEIGHT_FOR_EVERY_MEMBER")
    if not objective or not certificate or not certificate.get("global_weight_optimum_established"):
        _reject("MINIMUM_WEIGHT_REQUIRES_EXPLICIT_GLOBAL_OPTIMUM_CERTIFICATE")
    if certificate.get("problem_semantic_fingerprint") != core.provenance.problem_semantic_fingerprint:
        _reject("MINIMUM_WEIGHT_CERTIFICATE_FINGERPRINT_MISMATCH")
    return ConflictCore(
        provenance=core.provenance,
        members=core.members,
        stage="RECHECKED",
        claim=CoreClaim("MINIMUM_WEIGHT", True, evidence_ids, objective=objective, certificate=certificate),
        parent_core_fingerprint=core.fingerprint,
        transformation_evidence_ids=evidence_ids,
    )


def strongest_established_claim(core: ConflictCore) -> str:
    """Return only the claim explicitly established on this exact core.

    No ordering is used to infer stronger guarantees: irreducible is not minimum
    cardinality, and minimum cardinality is not minimum weight.
    """
    return core.claim.claim_kind if core.claim.established else "NONE"
