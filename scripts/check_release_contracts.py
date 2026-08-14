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
    if version != "0.47.0":
        raise SystemExit(f"unexpected release version: {version}")

    require(root / "src/aasm/__init__.py", ["public_v47"])
    require(root / "src/aasm/cli.py", ["cli_v47"])
    require(root / "src/aasm/public_v47.py", [
        '__version__ = "0.47.0"',
        '"contract_version": "0.23.0"',
        "CERTIFICATION_CONTRACT_VERSION",
        "SII_GOVERNED_CONTRACT_VERSION",
        "runtime_v47",
        "GOVERNED_ENFORCED",
        "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING",
        "NEVER_REDUCED_BY_SII",
    ])
    require(root / "src/aasm/runtime_v47.py", ["SIIGovernanceRuntimeMixin", "V46Engine"])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_ID = "aasm.sii.v1"',
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"',
        'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"',
        "SIIPrincipalBinding", "SIIScoringPolicy", "GovernedResourceLease",
        "DURABLE_POLICY_OR_CONTROLLER_ADMISSION", "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING",
        "VERSIONED_DURABLE_POLICY", "EXISTING_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_SOLVER_PATHS",
        "REQUIRED_VERIFICATION_NEVER_REDUCED", '"authority_reward": "NEVER"',
        "enforce_advanced_problem_budget", "outstanding_discretionary_tasks", "record_enforcement",
    ])
    require(root / "src/aasm/_runtime_v47_sii.py", [
        "request_sii_advanced_optimization", "request_sii_formal_verification",
        "sii_context", "sii_resource_lease", "priority=lease.budget.scheduler_priority",
        "SII max_parallel_candidates budget exhausted",
        "policy-required verification must use the ordinary formal path",
        '"authority_reward": "NEVER"',
    ])
    require(root / "src/aasm/certification_v47.py", [
        'CERTIFICATION_CONTRACT_VERSION = "0.2.0"',
        '"sii-preview": "sii-governance"',
        "measurement-principal-authority-binding",
        "versioned-scoring-policy-active",
        "resource-lease-native-solver-enforcement",
        "resource-lease-scheduler-enforcement",
        "mandatory-verification-not-reduced",
        "replay-preserves-governed-sii",
    ])
    require(root / "src/aasm/cli_v47.py", [
        "sii-governance-contract", "sii-default-scoring-policy",
        "certification_contract", "run_certification", "sii_contract",
    ])

    # Preserve v0.46/v0.45/v0.44/native/formal pathways as first-class APIs.
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
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "solver.convex", "cvxpy", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs", "PySATCadicalWorker", "ORToolsCPSATWorker", "HighsMILPWorker"])
    require(root / "src/aasm/formal_workers.py", ['provider == "z3"', 'provider == "cvc5"', 'provider == "vampire"', "lean4"])
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "OPTIMIZATION_RESULT"])

    require(root / "README.md", [
        "Current release — v0.47.0", "Governed Symbiotic Intelligence & Intelligence Economics",
        "aasm.adoption.v1 / 0.23.0", "aasm.certification.v1 / 0.2.0", "aasm.sii.v1 / 0.3.0",
        "Kissat", "CaDiCaL", "CP-SAT scheduling — OR-Tools", "HiGHS", "CVXPY", "PuLP",
        "Z3", "cvc5", "Vampire", "Lean 4", "Required verification is never reduced",
        "v0.48.0", "aasm.remote.v1 / 0.19.0",
    ])
    require(root / "ROADMAP.md", ["v0.47.0", "Governed Symbiotic Intelligence", "v0.48.0", "Cross-Run Certified Knowledge"])
    require(root / "CHANGELOG.md", ["[0.47.0]", "GOVERNED_ENFORCED", "REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.47.0", "runtime_v47", "0.23.0", "0.2.0", "0.3.0", "REQUIRED VERIFICATION IS NEVER REDUCED BY SII", "v0.48"])
    require(root / "docs/SII_GOVERNED_ECONOMICS.md", [
        "aasm.sii.v1 / 0.3.0", "GOVERNED_ENFORCED", "SIIPrincipalBinding", "SIIScoringPolicy",
        "GovernedResourceLease", "Incremental CaDiCaL", "TaskDemand", "TaskLease",
        "never reduced by SII", "sii-preview", "PASS",
    ])
    require(root / "docs/RELEASE_0.47.md", ["AASM v0.47.0", "0.23.0", "0.2.0", "0.3.0", "REQUIRED VERIFICATION IS NEVER REDUCED BY SII"])
    require(root / "tests/test_v47_public.py", ["0.47.0", "0.23.0", "0.2.0", "0.3.0", "sii-preview"])
    require(root / "tests/test_v47_sii_governance.py", ["measurement authority", "max_parallel_candidates", "authority_reward", "10_000", "20_000"])
    require(root / "tests/test_v47_sii_real.py", ["AASM_REQUIRE_SII_BACKENDS", "cadical-incremental", "authority_reward", "EVIDENCE_ONLY"])
    require(root / ".github/workflows/optimization.yml", [
        "AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS", "AASM_REQUIRE_ADVANCED_BACKENDS",
        "AASM_REQUIRE_SII_BACKENDS", "test_v47_sii_real.py", "certify --target sii-preview",
    ])

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
        "sii-principal-binding.schema.json", "sii-scoring-policy.schema.json", "sii-governed-resource-lease.schema.json",
        "reuse-request.schema.json", "reuse-certificate.schema.json", "certification-report.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.47 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
