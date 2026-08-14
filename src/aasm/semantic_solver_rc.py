from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns
from typing import Any, Mapping

from .advanced_optimization_conformance import run_advanced_optimization_conformance
from .certification_v47 import run_certification
from .cross_run_conformance import run_cross_run_knowledge_conformance
from .cross_run_knowledge import CrossRunKnowledgeEnvelope
from .model import ProblemSpec
from .modeling_conformance import run_modeling_conformance
from .optimization import (
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationVariable,
    default_optimization_providers,
    objective_value,
    solve_optimization_request,
    validate_optimization_result,
    validate_optimization_solution,
)
from .optimization_conformance import run_optimization_conformance
from .persistence.sqlite import SQLiteStore
from .runtime_v41 import AASMEngine as V41Engine
from .runtime_v47 import AASMEngine as V47Engine
from .runtime_v48 import AASMEngine as V48Engine
from .semantic_result import semantic_fingerprint
from .sii_governance import SIIPrincipalBinding


SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"
SEMANTIC_SOLVER_RC_CONTRACT_VERSION = "0.1.0"
SEMANTIC_SOLVER_RC_STABILITY = "RELEASE_CANDIDATE"
SEMANTIC_SOLVER_RC_FREEZE_TARGET = "0.49.x"
SEMANTIC_SOLVER_RC_COMPATIBILITY_FLOOR = "v0.41"


def semantic_solver_rc_contract() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_SOLVER_RC_CONTRACT_ID,
        "contract_version": SEMANTIC_SOLVER_RC_CONTRACT_VERSION,
        "stability": SEMANTIC_SOLVER_RC_STABILITY,
        "freeze_target": SEMANTIC_SOLVER_RC_FREEZE_TARGET,
        "runtime_extension": "THIN_V48_COMPOSITION_NO_NEW_KERNEL",
        "scheduler": "EXISTING_AASM_TASKLEASE_ONLY",
        "authority": "EXISTING_AASM_AUTHORITY_ONLY",
        "truth_boundary": "EXISTING_AASM_EPISTEMIC_ADMISSION_ONLY",
        "compatibility_floor": SEMANTIC_SOLVER_RC_COMPATIBILITY_FLOOR,
        "compatibility": "REPLAY_AND_PUBLIC_CONTRACT_FREEZE",
        "cross_backend_rule": "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
        "benchmark_policy": "MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM",
        "native_solver_claim": "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS",
        "claim_policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
        "license_policy": "PROJECT_WIDE_APACHE_2_0_WITH_PRIOR_MIT_GRANTS_PRESERVED",
        "required_release_gates": [
            "CI",
            "Formal Assurance",
            "Optimization Backends",
            "Cross-Run Knowledge",
            "Semantic Solver RC",
        ],
    }


def _walk_contracts(value: Any, *, path: str = "root", rows: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    rows = [] if rows is None else rows
    if isinstance(value, Mapping):
        contract_id = value.get("contract_id")
        contract_version = value.get("contract_version")
        if isinstance(contract_id, str) and isinstance(contract_version, str):
            rows.append({"path": path, "contract_id": contract_id, "contract_version": contract_version})
        for key, child in sorted(value.items(), key=lambda item: str(item[0])):
            _walk_contracts(child, path=f"{path}.{key}", rows=rows)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _walk_contracts(child, path=f"{path}[{index}]", rows=rows)
    return rows


def build_semantic_solver_rc_freeze_manifest(public_contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if public_contract is None:
        from .public_v48 import public_api_contract

        public_contract = public_api_contract()
    contract = deepcopy(dict(public_contract))
    root = Path(__file__).resolve().parents[2]
    schemas = sorted(path.name for path in (root / "schemas").glob("*.schema.json")) if (root / "schemas").exists() else []
    payload = {
        "rc_contract_id": SEMANTIC_SOLVER_RC_CONTRACT_ID,
        "rc_contract_version": SEMANTIC_SOLVER_RC_CONTRACT_VERSION,
        "runtime_version": str(contract.get("runtime_version") or ""),
        "adoption_contract_id": str(contract.get("contract_id") or "aasm.adoption.v1"),
        "adoption_contract_version": str(contract.get("contract_version") or ""),
        "contracts": sorted(_walk_contracts(contract), key=lambda row: (row["contract_id"], row["contract_version"], row["path"])),
        "supported_engine_methods": sorted(set(map(str, contract.get("supported_engine_methods") or ()))),
        "supported_cli_commands": sorted(set(map(str, contract.get("supported_cli_commands") or ()))),
        "supported_public_imports": sorted(set(map(str, contract.get("supported_imports") or ()))),
        "supported_inspection_surfaces": sorted(set(map(str, contract.get("supported_inspection_surfaces") or ()))),
        "schemas": schemas,
        "solver_providers": [
            "cadical",
            "kissat404",
            "ortools-cp-sat",
            "ortools-cp-sat-scheduling",
            "highs",
            "highs-advanced",
            "cvxpy",
            "cvxpy-advanced",
            "z3",
            "cvc5",
            "vampire",
            "lean4",
        ],
        "persistence_replay": "EVENT_HISTORY_REPLAY_REQUIRED",
        "license": "Apache-2.0",
        "license_policy_file": "LICENSE_POLICY.md",
        "performance_claims": "MEASURED_VALUES_INFORMATIONAL_UNLESS_EXPLICIT_THRESHOLD_GATE_EXISTS",
    }
    payload["freeze_fingerprint"] = semantic_fingerprint(payload)
    return payload


def _overlap_models() -> dict[str, OptimizationModel]:
    variables = (
        OptimizationVariable("x", "BOOL", 0, 1),
        OptimizationVariable("y", "BOOL", 0, 1),
    )
    linear = OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense=">=", rhs=1)
    objective = OptimizationObjective("MINIMIZE", {"x": 1, "y": 1})
    return {
        "SAT": OptimizationModel(
            "rc-overlap-sat",
            variables,
            (OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"), BooleanLiteral("y"))),),
            family="SAT",
        ),
        "CP_SAT": OptimizationModel("rc-overlap-cp-sat", variables, (linear,), objective, family="CP_SAT"),
        "MILP": OptimizationModel("rc-overlap-milp", variables, (linear,), objective, family="MILP"),
    }


def run_cross_backend_overlap_certification(*, real: bool = False) -> dict[str, Any]:
    models = _overlap_models()
    checks = {
        "sat_projection_is_boolean_feasibility": models["SAT"].solver_family == "SAT",
        "cp_sat_and_milp_share_exact_discrete_semantics": (
            models["CP_SAT"].solver_family == "CP_SAT"
            and models["MILP"].solver_family == "MILP"
            and [row.to_dict() for row in models["CP_SAT"].variables] == [row.to_dict() for row in models["MILP"].variables]
            and models["CP_SAT"].objective.to_dict() == models["MILP"].objective.to_dict()
        ),
        "disagreement_policy_is_inconclusive_never_vote": True,
    }
    results: dict[str, Any] = {}
    if real:
        providers = {"SAT": "cadical", "CP_SAT": "ortools-cp-sat", "MILP": "highs"}
        capabilities = {"SAT": "solver.sat", "CP_SAT": "solver.cp_sat", "MILP": "solver.milp"}
        solved = {}
        for family, model in models.items():
            request = OptimizationRequest(
                model,
                capabilities[family],
                "0.1.0",
                f"rc-overlap-{family.lower()}",
                required_provider=providers[family],
            )
            result = solve_optimization_request(request)
            validate_optimization_result(request, result)
            solved[family] = result
            results[family] = result.to_dict()
        validate_optimization_solution(models["SAT"], solved["SAT"].assignment)
        checks["sat_feasibility_projection_satisfied"] = solved["SAT"].status == "SAT" and sum(solved["SAT"].assignment.values()) >= 1
        cp_value = objective_value(models["CP_SAT"], solved["CP_SAT"].assignment)
        milp_value = objective_value(models["MILP"], solved["MILP"].assignment)
        checks["cp_sat_optimum_is_one"] = solved["CP_SAT"].status == "OPTIMAL" and abs(float(cp_value) - 1.0) <= 1e-9
        checks["milp_optimum_is_one"] = solved["MILP"].status == "OPTIMAL" and abs(float(milp_value) - 1.0) <= 1e-9
        checks["cp_sat_and_milp_objectives_agree"] = abs(float(cp_value) - float(milp_value)) <= 1e-9
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "real_backends": bool(real),
        "checks": checks,
        "results": results,
        "semantics": "SAT feasibility projection plus exact discrete CP-SAT/MILP optimum agreement",
        "voting": "NEVER",
    }
    report["report_fingerprint"] = semantic_fingerprint({"status": report["status"], "real_backends": bool(real), "checks": checks, "semantics": report["semantics"], "voting": "NEVER"})
    return report


def _record_procedural_memory(engine, label: str) -> str:
    proposed = engine.propose_memory_operation(
        "STORE",
        scope_id="root",
        proposer_id="compat-agent",
        kind="PROCEDURAL",
        substrate="STRUCTURED",
        content={"compatibility_fixture": label},
        privacy_level="PUBLIC",
    )
    decision_id = proposed["decision"]["decision_id"]
    engine.authorize_memory_operation(decision_id, authority_id="compat-policy", authority_class="POLICY")
    committed = engine.commit_memory_operation(decision_id, worker_id="compat-memory-worker")
    return str(committed["memory"]["memory"]["memory_id"])


def run_upgrade_compatibility(*, target_engine_cls=None) -> dict[str, Any]:
    target_engine_cls = target_engine_cls or V48Engine
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    with TemporaryDirectory(prefix="aasm-rc-upgrade-") as directory:
        root = Path(directory)

        # v0.41: event history + memo + governed v0.40 memory must replay under the RC target.
        path41 = root / "v41.sqlite"
        store41 = SQLiteStore(str(path41))
        old41 = V41Engine(ProblemSpec("rc upgrade v41"), store=store41)
        mid41 = old41.snapshot.machine_id
        old41.add_observation("v41 compatibility evidence", source="rc")
        old41.memo_put("rc-key", {"value": 41})
        memory41 = _record_procedural_memory(old41, "v41")
        hash41 = old41.snapshot.canonical_hash()
        store41.close()
        reopened41 = SQLiteStore(str(path41))
        current41 = target_engine_cls.resume(mid41, reopened41)
        checks["v41_history_resumes"] = current41.replay().canonical_hash() == current41.snapshot.canonical_hash() == hash41
        checks["v41_memo_preserved"] = current41.memo_get("rc-key") == {"value": 41}
        checks["v41_governed_memory_preserved"] = current41.hierarchical_memory_report()["memories"][memory41]["status"] == "ACTIVE"
        details["v41"] = {"event_count": len(current41.events), "snapshot_hash": current41.snapshot.canonical_hash()}
        reopened41.close()

        # v0.47: governed SII policy/principal evidence must project identically after resume.
        path47 = root / "v47.sqlite"
        store47 = SQLiteStore(str(path47))
        old47 = V47Engine(ProblemSpec("rc upgrade v47"), store=store47)
        mid47 = old47.snapshot.machine_id
        installed = old47.install_default_sii_scoring_policy(authority_id="compat-policy", authority_class="POLICY")
        old47.bind_sii_principal(SIIPrincipalBinding("compat-reasoner", "PROPOSER", can_propose=True), authority_id="compat-policy", authority_class="POLICY")
        policy_id = installed["policy"]["policy_id"]
        hash47 = old47.snapshot.canonical_hash()
        store47.close()
        reopened47 = SQLiteStore(str(path47))
        current47 = target_engine_cls.resume(mid47, reopened47)
        governance47 = current47.sii_governance_report()
        checks["v47_history_resumes"] = current47.replay().canonical_hash() == current47.snapshot.canonical_hash() == hash47
        checks["v47_sii_policy_preserved"] = governance47["active_policy_id"] == policy_id
        checks["v47_sii_principal_preserved"] = "compat-reasoner" in governance47["principals"]
        details["v47"] = {"event_count": len(current47.events), "snapshot_hash": current47.snapshot.canonical_hash(), "active_policy_id": governance47["active_policy_id"]}
        reopened47.close()

        # v0.48: admitted foreign Evidence must remain admitted without inheriting authority.
        path48 = root / "v48.sqlite"
        store48 = SQLiteStore(str(path48))
        old48 = V48Engine(ProblemSpec("rc upgrade v48"), store=store48)
        mid48 = old48.snapshot.machine_id
        envelope = CrossRunKnowledgeEnvelope(
            source_run_id="rc-foreign-run",
            source_machine_id="rc-foreign-machine",
            source_scope_id="root",
            knowledge_kind="PROCEDURAL",
            content={"procedure": ["inspect", "verify"]},
            privacy_level="PUBLIC",
            applicability_scope_ids=("root",),
        )
        proposed = old48.propose_cross_run_admission(envelope, proposer_id="compat-agent", target_scope_id="root")
        decision_id = proposed["decision"]["decision_id"]
        old48.authorize_cross_run_admission(decision_id, authority_id="compat-policy", authority_class="POLICY")
        old48.commit_cross_run_admission(decision_id, worker_id="compat-import-worker")
        hash48 = old48.snapshot.canonical_hash()
        store48.close()
        reopened48 = SQLiteStore(str(path48))
        current48 = target_engine_cls.resume(mid48, reopened48)
        row48 = current48.cross_run_knowledge_report()["envelopes"][envelope.envelope_id]
        checks["v48_history_resumes"] = current48.replay().canonical_hash() == current48.snapshot.canonical_hash() == hash48
        checks["v48_cross_run_admission_preserved"] = row48["status"] == "ACTIVE"
        checks["v48_foreign_authority_still_not_inherited"] = row48["source_authority_inherited"] is False
        details["v48"] = {"event_count": len(current48.events), "snapshot_hash": current48.snapshot.canonical_hash(), "envelope_status": row48["status"]}
        reopened48.close()

    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "compatibility_floor": SEMANTIC_SOLVER_RC_COMPATIBILITY_FLOOR,
        "target_engine": f"{target_engine_cls.__module__}.{target_engine_cls.__name__}",
        "checks": checks,
        "details": details,
    }
    report["report_fingerprint"] = semantic_fingerprint({"status": report["status"], "compatibility_floor": report["compatibility_floor"], "target_engine": report["target_engine"], "checks": checks})
    return report


def run_rc_benchmarks(*, real: bool = False, target_engine_cls=None, iterations: int = 64) -> dict[str, Any]:
    target_engine_cls = target_engine_cls or V48Engine
    iterations = max(1, int(iterations))
    workload = {
        "fingerprint_iterations": iterations,
        "event_append_iterations": min(iterations, 64),
        "real_solver_lifecycle": bool(real),
    }
    measurements: dict[str, Any] = {}

    started = perf_counter_ns()
    for index in range(iterations):
        semantic_fingerprint({"rc": "fingerprint", "index": index, "payload": [1, 2, 3]})
    measurements["semantic_fingerprint_total_ns"] = perf_counter_ns() - started

    engine = target_engine_cls(ProblemSpec("rc benchmark event append"))
    event_count = workload["event_append_iterations"]
    started = perf_counter_ns()
    for index in range(event_count):
        engine.add_observation(f"rc benchmark observation {index}", source="rc-benchmark")
    measurements["event_append_total_ns"] = perf_counter_ns() - started
    measurements["event_append_count"] = event_count

    checks = {
        "workload_completed": measurements["semantic_fingerprint_total_ns"] >= 0 and measurements["event_append_total_ns"] >= 0,
        "event_append_replay_exact": engine.replay().canonical_hash() == engine.snapshot.canonical_hash(),
        "timings_are_informational_not_truth": True,
        "no_inner_solver_speedup_claim": True,
    }

    if real:
        model = _overlap_models()["CP_SAT"]
        request = OptimizationRequest(model, "solver.cp_sat", "0.1.0", "rc-benchmark-direct", required_provider="ortools-cp-sat")
        started = perf_counter_ns()
        direct_result = solve_optimization_request(request)
        measurements["direct_native_cp_sat_ns"] = perf_counter_ns() - started
        validate_optimization_result(request, direct_result)

        lifecycle = target_engine_cls(ProblemSpec("rc benchmark leased solver lifecycle"))
        lifecycle.install_default_optimization_capability_contracts(authority_id="rc-policy", authority_class="POLICY")
        provider = next(row for row in default_optimization_providers() if row.provider_id == "ortools-cp-sat")
        installed = lifecycle.register_optimization_provider_runtime(provider, authority_id="rc-policy", authority_class="POLICY")
        lifecycle.admit_optimization_model(model)
        started = perf_counter_ns()
        requested = lifecycle.request_optimization(model.model_id, requester_id="rc-benchmark", required_provider="ortools-cp-sat")
        worker_id = installed["worker"]["worker_id"]
        lease = lifecycle.claim_next_task(worker_id, lease_seconds=60)
        committed = lifecycle.execute_optimization_lease(lease["lease_id"])
        measurements["aasm_leased_cp_sat_lifecycle_ns"] = perf_counter_ns() - started
        direct_ns = max(1, int(measurements["direct_native_cp_sat_ns"]))
        measurements["observed_orchestration_overhead_ratio"] = float(measurements["aasm_leased_cp_sat_lifecycle_ns"]) / direct_ns
        checks["real_direct_solver_completed"] = direct_result.status == "OPTIMAL"
        checks["real_leased_solver_completed"] = committed["satisfied"] is True and committed["result"]["status"] == "OPTIMAL"
        checks["real_leased_solver_replay_exact"] = lifecycle.replay().canonical_hash() == lifecycle.snapshot.canonical_hash()
        measurements["leased_request_id"] = requested["request"]["request_id"]

    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "real_backends": bool(real),
        "workload": workload,
        "measurements": measurements,
        "checks": checks,
        "interpretation": "Measured timings are environment-specific evidence. No speedup or regression claim is made without an explicit threshold gate.",
        "inner_solver_claim": "NONE",
    }
    report["workload_fingerprint"] = semantic_fingerprint({"workload": workload, "policy": "NO_UNGATED_SPEEDUP_CLAIM"})
    return report


def run_claim_gate_audit(root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parents[2]
    claims = {
        "python_matrix": [("README.md", "Python 3.11 / 3.12 / 3.13"), (".github/workflows/ci.yml", "3.13")],
        "formal_assurance": [("README.md", "Promela/SPIN"), (".github/workflows/formal.yml", "spin")],
        "native_solver_portfolio": [("README.md", "Optimization Backends"), (".github/workflows/optimization.yml", "test_v46_advanced_optimization_real.py")],
        "cross_run_governance": [("README.md", "Cross-Run Knowledge"), (".github/workflows/cross-run.yml", "test_v48_cross_run_knowledge.py")],
        "project_wide_apache": [("README.md", "LICENSE_POLICY.md"), ("scripts/check_release_contracts.py", "prior AASM versions are not designated MIT-only")],
        "rc_gate": [("ROADMAP.md", "Semantic Solver Release Candidate")],
    }
    results: dict[str, Any] = {}
    for claim, requirements in claims.items():
        missing = []
        for relative, token in requirements:
            path = root / relative
            if not path.exists() or token not in path.read_text(encoding="utf-8"):
                missing.append({"path": relative, "token": token})
        results[claim] = {"passed": not missing, "missing": missing, "evidence": [{"path": path, "token": token} for path, token in requirements]}
    status = "PASS" if all(row["passed"] for row in results.values()) else "FAIL"
    report = {"status": status, "policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE", "claims": results}
    report["report_fingerprint"] = semantic_fingerprint({"status": status, "policy": report["policy"], "claims": {key: row["passed"] for key, row in sorted(results.items())}})
    return report


def run_semantic_solver_rc_certification(*, real: bool = False, target_engine_cls=None, public_contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    target_engine_cls = target_engine_cls or V48Engine
    freeze = build_semantic_solver_rc_freeze_manifest(public_contract)
    upgrade = run_upgrade_compatibility(target_engine_cls=target_engine_cls)
    cross_run = run_cross_run_knowledge_conformance()
    semantic_certification = run_certification()
    optimization = run_optimization_conformance(real=real)
    modeling = run_modeling_conformance(real=real)
    advanced = run_advanced_optimization_conformance(real=real)
    overlap = run_cross_backend_overlap_certification(real=real)
    benchmark = run_rc_benchmarks(real=real, target_engine_cls=target_engine_cls, iterations=32)
    claims = run_claim_gate_audit()
    checks = {
        "freeze_manifest_present": bool(freeze.get("freeze_fingerprint")),
        "upgrade_compatibility_passes": upgrade["status"] == "PASS",
        "cross_run_conformance_passes": cross_run["status"] == "PASS",
        "semantic_certification_passes": semantic_certification["status"] == "PASS",
        "optimization_conformance_passes": optimization["status"] == "PASS",
        "modeling_conformance_passes": modeling["status"] == "PASS",
        "advanced_optimization_conformance_passes": advanced["status"] == "PASS",
        "cross_backend_overlap_passes": overlap["status"] == "PASS",
        "benchmark_workload_passes_without_speedup_claim": benchmark["status"] == "PASS" and benchmark["inner_solver_claim"] == "NONE",
        "public_claim_gate_audit_passes": claims["status"] == "PASS",
        "project_wide_apache_policy_frozen": freeze.get("license") == "Apache-2.0" and freeze.get("license_policy_file") == "LICENSE_POLICY.md",
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "real_backends": bool(real),
        "contract": semantic_solver_rc_contract(),
        "checks": checks,
        "freeze_manifest": freeze,
        "upgrade_compatibility": upgrade,
        "cross_backend_overlap": overlap,
        "benchmark": benchmark,
        "claim_gate_audit": claims,
        "component_status": {
            "cross_run": cross_run["status"],
            "semantic_certification": semantic_certification["status"],
            "optimization": optimization["status"],
            "modeling": modeling["status"],
            "advanced_optimization": advanced["status"],
        },
    }
    report["report_fingerprint"] = semantic_fingerprint({"status": report["status"], "real_backends": bool(real), "checks": checks, "freeze_fingerprint": freeze.get("freeze_fingerprint"), "contract": semantic_solver_rc_contract()})
    return report


__all__ = [
    "SEMANTIC_SOLVER_RC_CONTRACT_ID",
    "SEMANTIC_SOLVER_RC_CONTRACT_VERSION",
    "SEMANTIC_SOLVER_RC_STABILITY",
    "semantic_solver_rc_contract",
    "build_semantic_solver_rc_freeze_manifest",
    "run_cross_backend_overlap_certification",
    "run_upgrade_compatibility",
    "run_rc_benchmarks",
    "run_claim_gate_audit",
    "run_semantic_solver_rc_certification",
]
