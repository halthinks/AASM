from aasm.model import ProblemSpec
from aasm.runtime_v48 import AASMEngine as V48Engine
from aasm.runtime_v49 import AASMEngine as V49Engine
from aasm.semantic_solver_rc import (
    SEMANTIC_SOLVER_RC_CONTRACT_ID,
    SEMANTIC_SOLVER_RC_CONTRACT_VERSION,
    build_semantic_solver_rc_freeze_manifest,
    run_claim_gate_audit,
    run_cross_backend_overlap_certification,
    run_rc_benchmarks,
    run_semantic_solver_rc_certification,
    run_upgrade_compatibility,
    semantic_solver_rc_contract,
)


def test_rc_runtime_is_thin_v48_composition():
    assert issubclass(V49Engine, V48Engine)
    engine = V49Engine(ProblemSpec("v0.49 thin composition"))
    contract = engine.semantic_solver_rc_contract_report()
    assert contract["contract_id"] == SEMANTIC_SOLVER_RC_CONTRACT_ID
    assert contract["contract_version"] == SEMANTIC_SOLVER_RC_CONTRACT_VERSION
    assert contract["runtime_extension"] == "THIN_V48_COMPOSITION_NO_NEW_KERNEL"
    assert contract["scheduler"] == "EXISTING_AASM_TASKLEASE_ONLY"
    assert contract["authority"] == "EXISTING_AASM_AUTHORITY_ONLY"


def test_freeze_manifest_is_deterministic_for_same_public_contract():
    from aasm.public_v48 import public_api_contract

    contract = public_api_contract()
    first = build_semantic_solver_rc_freeze_manifest(contract)
    second = build_semantic_solver_rc_freeze_manifest(contract)
    assert first == second
    assert first["freeze_fingerprint"]
    assert first["license"] == "Apache-2.0"
    assert first["license_policy_file"] == "LICENSE_POLICY.md"
    assert "cadical" in first["solver_providers"]
    assert "lean4" in first["solver_providers"]


def test_dependency_neutral_overlap_certification_is_explicit_and_non_voting():
    report = run_cross_backend_overlap_certification(real=False)
    assert report["status"] == "PASS", report
    assert report["voting"] == "NEVER"
    assert report["checks"]["cp_sat_and_milp_share_exact_discrete_semantics"] is True
    assert report["checks"]["disagreement_policy_is_inconclusive_never_vote"] is True


def test_upgrade_compatibility_replays_v41_v47_v48_under_v49():
    report = run_upgrade_compatibility(target_engine_cls=V49Engine)
    assert report["status"] == "PASS", report
    assert report["compatibility_floor"] == "v0.41"
    assert all(report["checks"].values())
    assert report["checks"]["v41_memo_preserved"] is True
    assert report["checks"]["v47_sii_policy_preserved"] is True
    assert report["checks"]["v48_foreign_authority_still_not_inherited"] is True


def test_rc_benchmark_is_measurement_only_and_replay_checked():
    report = run_rc_benchmarks(real=False, target_engine_cls=V49Engine, iterations=8)
    assert report["status"] == "PASS", report
    assert report["inner_solver_claim"] == "NONE"
    assert "No speedup or regression claim" in report["interpretation"]
    assert report["checks"]["event_append_replay_exact"] is True
    assert report["workload_fingerprint"]


def test_claim_gate_audit_requires_reproducible_repository_evidence():
    report = run_claim_gate_audit()
    assert report["status"] == "PASS", report
    assert report["policy"] == "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"
    assert all(row["passed"] for row in report["claims"].values())


def test_dependency_neutral_rc_certification_passes():
    from aasm.public_v48 import public_api_contract

    report = run_semantic_solver_rc_certification(real=False, target_engine_cls=V49Engine, public_contract=public_api_contract())
    assert report["status"] == "PASS", report
    assert report["real_backends"] is False
    assert all(report["checks"].values())
    assert report["benchmark"]["inner_solver_claim"] == "NONE"
    assert report["contract"]["native_solver_claim"] == "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS"


def test_runtime_rc_facade_delegates_without_new_authority():
    from aasm.public_v48 import public_api_contract

    engine = V49Engine(ProblemSpec("rc facade"))
    manifest = engine.semantic_solver_rc_freeze_manifest(public_api_contract())
    assert manifest["freeze_fingerprint"]
    assert engine.semantic_solver_rc_claim_audit()["status"] == "PASS"
    assert engine.semantic_solver_rc_cross_backend_report(real=False)["status"] == "PASS"


def test_rc_contract_freezes_no_ungated_performance_claim():
    contract = semantic_solver_rc_contract()
    assert contract["benchmark_policy"] == "MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM"
    assert contract["native_solver_claim"] == "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS"
    assert contract["claim_policy"] == "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"
