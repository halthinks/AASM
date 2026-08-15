from pathlib import Path
import tomllib


def require(path, tokens):
    text = Path(path).read_text()
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")


def forbid(path, tokens):
    text = Path(path).read_text()
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden stale policy text {present}")


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    version = str(project["version"])
    if version != "0.52.0":
        raise SystemExit(f"unexpected release version: {version}")

    # Project-wide Apache-2.0 / PEP 639 packaging remains permanent.
    if project.get("license") != "Apache-2.0":
        raise SystemExit(f"unexpected active license: {project.get('license')}")
    if set(project.get("license-files", [])) != {"LICENSE", "NOTICE", "LICENSE_POLICY.md"}:
        raise SystemExit(f"unexpected license files: {project.get('license-files')}")
    if [value for value in project.get("classifiers", []) if value.startswith("License ::")]:
        raise SystemExit("PEP 639 license expression must not use legacy license classifiers")
    require(root / "LICENSE", ["Apache License", "Version 2.0, January 2004", "Grant of Patent License", "END OF TERMS AND CONDITIONS"])
    require(root / "NOTICE", ["AASM", "Copyright 2026 AASM contributors"])
    require(root / "LICENSE_POLICY.md", [
        "all AASM source code, documentation, tags, commits, and release versions are offered under Apache-2.0",
        "Earlier MIT grants remain valid",
        "prior AASM versions are not designated MIT-only",
    ])
    require(root / "MANIFEST.in", ["LICENSE NOTICE LICENSE_POLICY.md pyproject.toml"])

    stale_license_policy = [
        "v0.47.1 is the first Apache-2.0 AASM release",
        "remains the original MIT-licensed distribution",
        "already-published `v0.47.0` release remains under the MIT License",
    ]
    for policy_doc in (root / "README.md", root / "ROADMAP.md", root / "CHANGELOG.md", root / "docs/CURRENT_RELEASE.md"):
        forbid(policy_doc, stale_license_policy)

    # Current v0.52 active public surface.
    require(root / "src/aasm/__init__.py", ["public_v52"])
    require(root / "src/aasm/cli.py", ["cli_v52"])
    require(root / "src/aasm/public_v52.py", [
        '__version__ = "0.52.0"', '"contract_version": "0.28.0"', "runtime_v52",
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "MULTI_OBJECTIVE_CONTRACT_ID", "FRONTIER_CONTRACT_ID", "RESOURCE_ROUTING_CONTRACT_ID",
        '"resource_state_authority": "NEVER_GRANTS_AUTHORITY"',
        '"observation_truth": "EVIDENCE_ONLY"',
        '"candidate_frontier_scope": "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY"',
        '"authority_reward": "NEVER"',
    ])
    require(root / "src/aasm/runtime_v52.py", [
        "V51Engine", "solve_lexicographic_multi_objective", "solve_exact_pareto_multi_objective",
        "record_resource_candidate_pareto_frontier", "pareto_resource_aware_sii_proposals",
        '"authority": "EVIDENCE_ONLY"',
    ])
    require(root / "src/aasm/multi_objective.py", [
        'MULTI_OBJECTIVE_CONTRACT_ID = "aasm.optimization.multi-objective.v1"',
        'FRONTIER_CONTRACT_ID = "aasm.optimization.frontier.v1"',
        '"exact_finite_basis": "V0.51_COMPLETE_FINITE_ENUMERATION_CERTIFICATE_REQUIRED"',
        '"result_authority": "EVIDENCE_ONLY"', '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
        "exact_points_match = actual_by_id == expected_by_id",
        "enumeration_certificate.certificate_id != independent_certificate.certificate_id",
    ])
    require(root / "src/aasm/resource_routing.py", [
        'RESOURCE_ROUTING_CONTRACT_ID = "aasm.resource.routing.v1"',
        "ResourceRoutingObjective", "resource_candidate_pareto_frontier",
        '"provider_quota_burn"', '"monetary_cost"', '"wall_time_seconds"', '"scarce_expert_usage"',
        '"authority": "EVIDENCE_ONLY"',
    ])
    require(root / "src/aasm/_runtime_v52_resources.py", [
        'RESOURCE_RUNTIME_CONTRACT_ID = "aasm.resource.runtime.v1"',
        'RESOURCE_RUNTIME_CONTRACT_VERSION = "0.1.0"',
        '"authority": "RESOURCE_STATE_NEVER_GRANTS_AUTHORITY"',
        '"truth": "RESOURCE_OBSERVATIONS_REMAIN_EVIDENCE"',
        "reestimate_resource_reservation", "release_resource_reservation", "settle_resource_reservation",
    ])
    require(root / "src/aasm/sii_v52.py", [
        'SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID = "aasm.sii.resource-aware-proposal.v1"',
        "expected_provider_quota_burn", "ResourceAwareStructuredProposal",
    ])
    require(root / "src/aasm/cli_v52.py", ["multi-objective-contract", "pareto-frontier-contract", "resource-routing-contract"])
    require(root / "tests/test_v52_public.py", ["0.52.0", "0.28.0", "ACTIVE_DEVELOPMENT"])
    require(root / "tests/test_v52_multi_objective.py", ["exact_solution_set_match", "falsified_point_content"])

    # v0.51 remains the frozen parent for v0.52 enumeration and proof lineage.
    require(root / "src/aasm/public_v51.py", [
        '__version__ = "0.51.0"', '"contract_version": "0.27.0"', "runtime_v51",
        "SOLUTION_POOL_CONTRACT_ID", "ENUMERATION_CONTRACT_ID",
    ])
    require(root / "src/aasm/solution_pools.py", [
        'SOLUTION_POOL_CONTRACT_ID = "aasm.optimization.solution-pool.v1"',
        'ENUMERATION_CONTRACT_ID = "aasm.optimization.enumeration.v1"',
        '"complete_requires_independent_exhaustion_certificate": True',
        '"bounded_or_native_pool_implies_completeness": False',
        "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING",
    ])
    require(root / "src/aasm/solution_pool_conformance.py", ["false_completeness_fails_closed", "real_cross_backend_exact_solution_set"])

    # Preserve frozen proof/RC/cross-run/SII parent boundaries.
    require(root / "src/aasm/public_v50.py", ['__version__ = "0.50.0"', '"contract_version": "0.26.0"'])
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        '"proof_certified_requires_independent_checker": True', '"certificate_authority": "EVIDENCE_ONLY"',
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE", "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
    ])
    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"', '"authority_transfer": "NEVER"',
    ])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"', "REQUIRED_VERIFICATION_NEVER_REDUCED", '"authority_reward": "NEVER"',
    ])

    # Native/modeling/formal pathways remain first-class.
    require(root / "src/aasm/advanced_optimization.py", ["SEARCH_STATE_NEVER_PROMOTES_TRUTH", "EPHEMERAL_PERFORMANCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs"])
    require(root / "src/aasm/formal_workers.py", ['provider == "z3"', 'provider == "cvc5"', 'provider == "vampire"', "lean4"])

    # Release gates now include the v0.52 exact-SHA optimization status.
    require(root / ".github/workflows/optimization.yml", [
        "v0.52 contract and adversarial gate", "tests/test_v52_public.py", "aasm/optimization",
        "AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS",
    ])
    require(root / ".github/workflows/release.yml", [
        "aasm/ci-summary", "aasm/formal-assurance", "aasm/semantic-solver-rc", "aasm/proof-claims",
        "aasm/solution-pools", "aasm/optimization", "Require exact main commit and all release gates",
    ])
    require(root / ".github/workflows/proof-claims.yml", ["aasm/proof-claims"])
    require(root / ".github/workflows/solution-pools.yml", ["aasm/solution-pools"])
    require(root / ".github/workflows/rc.yml", ["aasm/semantic-solver-rc"])

    # v0.52 schemas must remain explicit wire contracts.
    for name in (
        "multi-objective-problem.schema.json", "lexicographic-result.schema.json",
        "pareto-frontier.schema.json", "pareto-frontier-certificate.schema.json",
        "resource-capacity.schema.json", "resource-observation.schema.json", "resource-demand.schema.json",
        "resource-routing-policy.schema.json", "sii-resource-aware-proposal.schema.json",
        "solution-record.schema.json", "solution-pool.schema.json",
        "enumeration-cursor.schema.json", "enumeration-completeness-certificate.schema.json",
        "solver-claim.schema.json", "solver-proof-artifact.schema.json", "solver-claim-certificate.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    extras = project["optional-dependencies"]
    optimization = " ".join(extras.get("optimization", []))
    modeling = " ".join(extras.get("modeling", []))
    for token in ("python-sat", "ortools", "highspy", "cvxpy", "pulp"):
        if token not in optimization:
            raise SystemExit(f"optimization extra missing {token}")
    for token in ("cvxpy", "pulp"):
        if token not in modeling:
            raise SystemExit(f"modeling extra missing {token}")

    print("v0.52.0 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
