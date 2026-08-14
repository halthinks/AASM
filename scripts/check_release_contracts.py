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
        version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.45.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v45"])
    require(root / "src/aasm/cli.py", ["cli_v45"])
    require(root / "src/aasm/public_v45.py", [
        '__version__ = "0.45.0"',
        '"contract_version": "0.21.0"',
        "CONVEX_OPTIMIZATION_CONTRACT_ID",
        "PULP_ADAPTER_CONTRACT_ID",
        "runtime_v45",
        "EVIDENCE_ONLY",
        "TRANSLATION_ONLY",
    ])
    require(root / "src/aasm/runtime_v45.py", ["ConvexOptimizationRuntimeMixin", "V44Engine"])
    require(root / "src/aasm/convex_optimization.py", [
        "aasm.optimization.convex.v1", "solver.convex", "cvxpy", "CONVEX_QP", "SOC",
        "EXISTING_AASM_RESOURCE_WORKER_LEASE", "EVIDENCE_ONLY", "CLARABEL", "OSQP",
    ])
    require(root / "src/aasm/pulp_adapter.py", [
        "aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"',
        "REJECT_NOT_APPROXIMATE", "pulp_problem_to_optimization_model",
    ])
    require(root / "src/aasm/_runtime_v45_convex.py", [
        "register_default_cvxpy_provider_runtime", "request_convex_optimization", "commit_convex_result",
        "execute_convex_lease", "convex_reuse_request", "import_pulp_problem", "optimization-solver",
    ])
    require(root / "src/aasm/modeling_conformance.py", ["run_modeling_conformance", "cvxpy", "pulp"])
    require(root / "src/aasm/cli_v45.py", ["convex-optimization-contract", "pulp-adapter-contract", "modeling-conformance", "--real"])

    # v0.44 native and v0.39 formal paths remain first-class.
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs", "PySATCadicalWorker", "ORToolsCPSATWorker", "HighsMILPWorker"])
    require(root / "src/aasm/formal_workers.py", ['provider == "z3"', 'provider == "cvc5"', 'provider == "vampire"', "lean4"])
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "OPTIMIZATION_RESULT"])

    require(root / "README.md", [
        "Current release — v0.45.0", "Convex Optimization & Modeling Adapters", "CVXPY", "PuLP",
        "CaDiCaL", "OR-Tools CP-SAT", "HiGHS", "Z3", "cvc5", "Vampire", "Lean 4",
        "aasm.adoption.v1 / 0.21.0", "aasm.optimization.convex.v1 / 0.1.0", "aasm.adapter.pulp.v1 / 0.1.0", "v0.46.0",
    ])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.45.0", "runtime_v45", "0.21.0", "CVXPY", "PuLP", "v0.46"])
    require(root / "docs/CONVEX_AND_MODELING_ADAPTERS.md", ["solver.convex", "CVXPY", "PuLP", "EVIDENCE_ONLY", "translation-only", "HiGHS"])
    require(root / "docs/RELEASE_0.45.md", ["AASM v0.45.0", "CVXPY", "PuLP", "0.21.0"])
    require(root / "tests/test_v45_public.py", ["0.45.0", "0.21.0", "TRANSLATION_ONLY", "NEVER"])
    require(root / "tests/test_v45_modeling_adapters.py", ["EVIDENCE_ONLY", "TRANSLATION_ONLY", "solver_execution"])
    require(root / "tests/test_v45_modeling_adapters_real.py", ["AASM_REQUIRE_MODELING_BACKENDS", "cvxpy", "pulp", "highs"])
    require(root / ".github/workflows/optimization.yml", ["AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS", "modeling-conformance", "--real"])

    with (root / "pyproject.toml").open("rb") as handle:
        extras = tomllib.load(handle)["project"]["optional-dependencies"]
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
        "reuse-request.schema.json", "reuse-certificate.schema.json", "certification-report.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.45 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
