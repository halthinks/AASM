from __future__ import annotations

import pytest

from aasm.core_conflict import CoreMember, CoreProvenance, CoreRecheck
from aasm.core_conflict_runtime import (
    CoreConflictRejected,
    capture_raw_core,
    certify_irreducible,
    certify_minimum_cardinality,
    certify_minimum_weight,
    normalize_core,
    reduce_core,
    strongest_established_claim,
)

FP = "a" * 64


def provenance() -> CoreProvenance:
    return CoreProvenance(
        problem_revision_id="revision-7",
        problem_semantic_fingerprint=FP,
        solver_backend="solver-x",
        solver_backend_version="3.2",
        solver_run_id="run-1",
        solver_evidence_ids=("ev-solver",),
        external_result_id="result-99",
    )


def member(name: str, weight: float | None = 1.0) -> CoreMember:
    return CoreMember(
        external_reference_id=f"backend:{name}",
        normalized_reference_id=name,
        reference_kind="CONSTRAINT",
        source_scope_id="scope-1",
        source_fingerprint=FP,
        weight=weight,
    )


def base_core():
    raw = capture_raw_core(provenance=provenance(), members=(member("c1"), member("c2"), member("c3")), evidence_ids=("ev-raw",))
    return normalize_core(raw=raw, members=raw.members, evidence_ids=("ev-normalize",))


def recheck(core, checked, outcome, evidence, independent=True):
    return CoreRecheck(
        source_core_fingerprint=core.fingerprint,
        problem_semantic_fingerprint=FP,
        checked_member_ids=tuple(checked),
        outcome=outcome,
        verifier_id="independent-verifier",
        evidence_ids=(evidence,),
        independent_from_solver_run=independent,
    )


def test_raw_normalized_reduced_preserve_external_references_and_parent_chain() -> None:
    normalized = base_core()
    reduced = reduce_core(parent=normalized, members=normalized.members[:2], evidence_ids=("ev-reduce",))
    assert reduced.parent_core_fingerprint == normalized.fingerprint
    assert {m.external_reference_id for m in reduced.members} == {"backend:c1", "backend:c2"}
    assert strongest_established_claim(reduced) == "NONE"


def test_smaller_core_is_not_automatically_irreducible_or_minimum() -> None:
    normalized = base_core()
    reduced = reduce_core(parent=normalized, members=normalized.members[:2], evidence_ids=("ev-reduce",))
    assert reduced.cardinality == 2
    assert reduced.claim.claim_kind == "CONFLICT_PRESERVING"
    assert reduced.claim.established is False
    assert strongest_established_claim(reduced) == "NONE"


def test_budget_exhaustion_is_partial_not_minimum() -> None:
    normalized = base_core()
    partial = reduce_core(parent=normalized, members=normalized.members[:2], evidence_ids=("ev-budget",), budget_exhausted=True)
    assert strongest_established_claim(partial) == "BUDGET_LIMITED_PARTIAL"
    assert partial.claim.budget_exhausted is True


def test_irreducible_requires_independent_full_and_every_single_removal_recheck() -> None:
    core = reduce_core(parent=base_core(), members=base_core().members[:2], evidence_ids=("ev-reduce",))
    full = recheck(core, ("c1", "c2"), "CONFLICT", "ev-full")
    removals = {
        "c1": recheck(core, ("c2",), "SATISFIABLE", "ev-rm-c1"),
        "c2": recheck(core, ("c1",), "SATISFIABLE", "ev-rm-c2"),
    }
    certified = certify_irreducible(core=core, full_recheck=full, removal_rechecks=removals)
    assert strongest_established_claim(certified) == "IRREDUCIBLE"
    assert certified.stage == "RECHECKED"

    with pytest.raises(CoreConflictRejected, match="ONE_REMOVAL_RECHECK_PER_MEMBER"):
        certify_irreducible(core=core, full_recheck=full, removal_rechecks={"c1": removals["c1"]})


def test_irreducible_does_not_imply_minimum_cardinality() -> None:
    core = reduce_core(parent=base_core(), members=base_core().members[:2], evidence_ids=("ev-reduce",))
    full = recheck(core, ("c1", "c2"), "CONFLICT", "ev-full")
    irreducible = certify_irreducible(core=core, full_recheck=full, removal_rechecks={
        "c1": recheck(core, ("c2",), "SATISFIABLE", "ev-rm-c1"),
        "c2": recheck(core, ("c1",), "SATISFIABLE", "ev-rm-c2"),
    })
    assert strongest_established_claim(irreducible) == "IRREDUCIBLE"
    with pytest.raises(CoreConflictRejected, match="EXHAUSTIVE_CERTIFICATE"):
        certify_minimum_cardinality(core=irreducible, evidence_ids=("ev-min",), certificate={})


def test_minimum_cardinality_requires_same_semantic_fingerprint_certificate() -> None:
    core = base_core()
    with pytest.raises(CoreConflictRejected, match="FINGERPRINT_MISMATCH"):
        certify_minimum_cardinality(
            core=core,
            evidence_ids=("ev-min",),
            certificate={"exhaustive_smaller_cardinalities_checked": True, "problem_semantic_fingerprint": "b" * 64},
        )
    certified = certify_minimum_cardinality(
        core=core,
        evidence_ids=("ev-min",),
        certificate={"exhaustive_smaller_cardinalities_checked": True, "problem_semantic_fingerprint": FP},
    )
    assert strongest_established_claim(certified) == "MINIMUM_CARDINALITY"


def test_minimum_weight_is_independent_claim_with_explicit_objective_and_certificate() -> None:
    core = base_core()
    with pytest.raises(CoreConflictRejected, match="GLOBAL_OPTIMUM_CERTIFICATE"):
        certify_minimum_weight(core=core, evidence_ids=("ev-weight",), objective={"metric": "sum_member_weight"}, certificate={})
    certified = certify_minimum_weight(
        core=core,
        evidence_ids=("ev-weight",),
        objective={"metric": "sum_member_weight", "weights_fingerprint": "weights-v1"},
        certificate={"global_weight_optimum_established": True, "problem_semantic_fingerprint": FP},
    )
    assert strongest_established_claim(certified) == "MINIMUM_WEIGHT"
    assert certified.total_weight == 3.0


def test_cross_revision_or_member_identity_drift_fails_closed() -> None:
    normalized = base_core()
    drifted = CoreMember(
        external_reference_id="backend:c1",
        normalized_reference_id="c1",
        reference_kind="CONSTRAINT",
        source_scope_id="scope-1",
        source_fingerprint=FP,
        weight=9.0,
    )
    with pytest.raises(CoreConflictRejected, match="MEMBER_IDENTITY_DRIFT"):
        reduce_core(parent=normalized, members=(drifted,), evidence_ids=("ev-reduce",))


def test_round_trip_is_deterministic() -> None:
    core = base_core()
    restored = type(core).from_dict(core.to_dict())
    assert restored == core
    assert restored.fingerprint == core.fingerprint
