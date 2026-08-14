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
    if version != "0.44.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v44"])
    require(root / "src/aasm/cli.py", ["cli_v44"])
    require(
        root / "src/aasm/public_v44.py",
        [
            '__version__ = "0.44.0"',
            '"contract_version": "0.20.0"',
            "OPTIMIZATION_CONTRACT_ID",
            "runtime_v44",
            "optimization-portfolio",
        ],
    )
    require(root / "src/aasm/runtime_v44.py", ["OptimizationRuntimeMixin", "V41Engine"])
    require(
        root / "src/aasm/optimization.py",
        [
            "aasm.optimization.v1",
            "AASM_OWNED",
            "NATIVE_SOLVER_PROVIDER",
            "EXISTING_AASM_RESOURCE_WORKER_LEASE",
            "EVIDENCE_ONLY",
            "cadical",
            "ortools-cp-sat",
            "highs",
            "z3",
            "cvc5",
            "vampire",
            "lean4",
            "PySATCadicalWorker",
            "ORToolsCPSATWorker",
            "HighsMILPWorker",
        ],
    )
    require(
        root / "src/aasm/_runtime_v44_optimization.py",
        [
            "register_optimization_provider_runtime",
            "request_optimization",
            "commit_optimization_result",
            "execute_optimization_lease",
            "optimization_reuse_request",
            "optimization-solver",
            "result_authority",
            "EVIDENCE_ONLY",
        ],
    )
    require(root / "src/aasm/optimization_conformance.py", ["run_optimization_conformance", "real_backends"])
    require(root / "src/aasm/cli_v44.py", ["optimization-contract", "optimization-blueprint", "optimization-conformance", "--real"])

    # v0.43 certification and staged SII remain intact above the solver kernel.
    require(root / "src/aasm/certification.py", ["aasm.certification.v1", "PASS", "FAIL", "INCONCLUSIVE", "sii-preview"])
    require(root / "src/aasm/sii.py", ["aasm.sii.v1", "authority_reward", "NEVER", "direct_truth_promotion", "self_verification"])

    # Existing formal and reuse pathways remain active rather than being replaced.
    require(root / "src/aasm/formal_workers.py", ["provider == \"z3\"", "provider == \"cvc5\"", "provider == \"vampire\"", "lean4"])
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "INDEX_AND_VALIDATE_ONLY", "EXPLICIT_VALIDATOR_REQUIRED"])
    require(root / "src/aasm/_runtime_v41_solver.py", ["def solver_step", "SKIP_EXECUTION", "ROUTE_CAPABILITY"])

    require(
        root / "README.md",
        [
            "Current release — v0.44.0",
            "Heterogeneous Optimization Solver Portfolio",
            "CaDiCaL",
            "OR-Tools CP-SAT",
            "HiGHS",
            "Z3",
            "cvc5",
            "Vampire",
            "Lean 4",
            "aasm.adoption.v1 / 0.20.0",
            "aasm.optimization.v1 / 0.1.0",
            "v0.45.0",
        ],
    )
    require(
        root / "docs/CURRENT_RELEASE.md",
        ["AASM v0.44.0", "aasm.optimization.v1", "runtime_v44", "0.20.0", "v0.45"],
    )
    require(
        root / "docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md",
        ["Canonical Constraint IR", "CaDiCaL", "CP-SAT", "HiGHS", "Z3", "cvc5", "Vampire", "Lean 4", "reuse"],
    )
    require(root / "tests/test_v44_optimization.py", ["0.44.0", "0.20.0", "SKIP_EXECUTION", "EVIDENCE_ONLY"])
    require(root / "tests/test_v44_optimization_real.py", ["cadical", "ortools-cp-sat", "highs", "AASM_REQUIRE_OPTIMIZATION_BACKENDS"])
    require(root / ".github/workflows/optimization.yml", ["optimization", "--real", "AASM_REQUIRE_OPTIMIZATION_BACKENDS"])

    for name in (
        "reuse-request.schema.json",
        "reuse-certificate.schema.json",
        "solver-step.schema.json",
        "reference-domain-stress-report.schema.json",
        "certification-report.schema.json",
        "sii-proposal.schema.json",
        "sii-outcome.schema.json",
        "sii-resource-lease.schema.json",
        "optimization-model.schema.json",
        "optimization-request.schema.json",
        "optimization-result.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.44 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
