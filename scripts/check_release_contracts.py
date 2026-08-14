from pathlib import Path
import tomllib


def require(path, tokens):
    text = Path(path).read_text()
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
        version = str(project["version"])
    if version != "0.46.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v46"])
    require(root / "src/aasm/cli.py", ["cli_v46"])
    require(root / "src/aasm/public_v46.py", [
        '__version__ = "0.46.0"',
        '"contract_version": "0.22.0"',
        "ADVANCED_OPTIMIZATION_CONTRACT_ID",
        "runtime_v46",
        "SEARCH_STATE_NEVER_PROMOTES_TRUTH",
        "EPHEMERAL_PERFORMANCE_ONLY",
    ])
    require(root / "src/aasm/runtime_v46.py", ["AdvancedOptimizationRuntimeMixin", "V45Engine", "execute_advanced_optimization_lease", "advanced_execution"])
    require(root / "src/aasm/advanced_optimization.py", [
        "aasm.optimization.advanced.v1", "AASM_OWNED_EXPLICIT_SEARCH_ARTIFACTS",
        "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "SEARCH_STATE_NEVER_PROMOTES_TRUTH",
        "EPHEMERAL_PERFORMANCE_ONLY", "FAST_SAT", "INCREMENTAL_SAT", "CP_SAT_SCHEDULING",
        "MILP_ADVANCED", "CONVEX_ADVANCED", "cadical-incremental", "ortools-cp-sat-scheduling",
        "highs-advanced", "cvxpy-advanced", "unsat_core", "warm_start", "affine_soc",
    ])
    require(root / "src/aasm/advanced_execution.py", ["Kissat404", "pysat:kissat404", "aggregate_statistics_exposed", "non_incremental"])
    require(root / "src/aasm/_runtime_v46_advanced.py", [
        "register_advanced_optimization_provider_runtime", "request_advanced_optimization",
        "commit_advanced_optimization_result", "execute_advanced_optimization_lease",
        "advanced_optimization_reuse_request", "advanced result lease expired before result commit",
        "advanced result lease was superseded by a newer attempt",
        "advanced result implementation does not match admitted provider", "result_authority", "EVIDENCE_ONLY",
    ])
    require(root / "src/aasm/advanced_optimization_conformance.py", ["run_advanced_optimization_conformance", "incremental_sat_session_reused", "milp_bound_telemetry_present"])
    require(root / "src/aasm/cli_v46.py", ["advanced-optimization-contract", "advanced-optimization-blueprint", "advanced-optimization-conformance", "--real"])

    # Preserve the released v0.45/v0.44/native/formal pathways.
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "solver.convex", "cvxpy", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs", "PySATCadicalWorker", "ORToolsCPSATWorker", "HighsMILPWorker"])
    require(root / "src/aasm/formal_workers.py", ['provider == "z3"', 'provider == "cvc5"', 'provider == "vampire"', "lean4"])
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "OPTIMIZATION_RESULT"])

    require(root / "README.md", [
        "Current release — v0.46.0", "Advanced Solver Control & Search Artifacts", "Kissat", "CaDiCaL",
        "OR-Tools CP-SAT", "HiGHS", "CVXPY", "PuLP", "Z3", "cvc5", "Vampire", "Lean 4",
        "aasm.adoption.v1 / 0.22.0", "aasm.optimization.advanced.v1 / 0.1.0", "v0.47.0",
        "aasm.remote.v1 / 0.19.0",
    ])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.46.0", "runtime_v46", "0.22.0", "Kissat", "UNSAT core", "warm start", "v0.47"])
    require(root / "docs/ADVANCED_SOLVER_CONTROL.md", ["Kissat", "incremental CaDiCaL", "NO_OVERLAP", "CUMULATIVE", "warm start", "affine SOC", "EVIDENCE_ONLY", "EPHEMERAL_PERFORMANCE_ONLY"])
    require(root / "docs/RELEASE_0.46.md", ["AASM v0.46.0", "0.22.0", "Kissat", "CaDiCaL", "CP-SAT", "HiGHS", "CVXPY"])
    require(root / "tests/test_v46_public.py", ["0.46.0", "0.22.0", "SEARCH_STATE_NEVER_PROMOTES_TRUTH"])
    require(root / "tests/test_v46_advanced_optimization.py", ["EVIDENCE_ONLY", "EPHEMERAL_PERFORMANCE_ONLY", "forged-backend"])
    require(root / "tests/test_v46_advanced_optimization_real.py", ["AASM_REQUIRE_ADVANCED_BACKENDS", "FAST_SAT", "INCREMENTAL_SAT", "CP_SAT_SCHEDULING", "MILP_ADVANCED", "CONVEX_ADVANCED"])
    require(root / ".github/workflows/optimization.yml", ["AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS", "AASM_REQUIRE_ADVANCED_BACKENDS", "advanced_optimization_conformance"])

    extras = project["optional-dependencies"]
    optimization = " ".join(extras.get("optimization", []))
    modeling = " ".join(extras.get("modeling", []))
    for token in ("python-sat", "ortools", "highspy", "cvxpy", "pulp"):
        if token not in optimization:
            raise SystemExit(f"optimization extra missing {token}")
    for token in ("cvxpy", "pulp"):
        if token not in modeling:
            raise SystemExit(f"modeling extra missing {token}")

    for name in (
        "optimization-model.schema.json", "optimization-request.schema.json", "optimization-result.schema.json",
        "convex-optimization-model.schema.json", "convex-optimization-request.schema.json", "convex-optimization-result.schema.json",
        "advanced-optimization-problem.schema.json", "advanced-optimization-request.schema.json", "advanced-optimization-result.schema.json",
        "reuse-request.schema.json", "reuse-certificate.schema.json", "certification-report.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.46 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
