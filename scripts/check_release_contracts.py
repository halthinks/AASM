from pathlib import Path
import subprocess
import sys
import tomllib


def require(path, tokens):
    text = Path(path).read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")


def forbid(path, tokens):
    text = Path(path).read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden stale policy text {present}")


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    version = str(project["version"])
    if version != "0.53.0":
        raise SystemExit(f"unexpected release version: {version}")

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

    # Current v0.53 public surface.
    require(root / "src/aasm/__init__.py", ["public_v53"])
    require(root / "src/aasm/cli.py", ["cli_v53"])
    require(root / "src/aasm/public_v53.py", [
        '__version__ = "0.53.0"',
        '"contract_version": "0.29.0"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "runtime_v53_learning",
        "SCOPED_AUTHORITY_CONTRACT_ID",
        "SCOPED_STORE_CONTRACT_ID",
        "SOLVER_LEARNING_CONTRACT_ID",
        "SOLVER_LEARNING_APPLICATION_CONTRACT_ID",
        '"cross_run_authority_transfer"',
        '"application_truth_authority"',
        '"application_policy_authority"',
    ])
    require(root / "src/aasm/runtime_v53.py", [
        "PrincipalAwareResourceHistoryMixin",
        "ScopedAuthorityRuntimeMixin",
        "_guard_resource_evidence_by_version = True",
        "RESOURCE_AUTHORITY_CAPABILITIES",
        "EFFECT_AUTHORITY_CAPABILITIES",
    ])
    require(root / "src/aasm/runtime_v53_learning.py", [
        "SolverLearningRuntimeMixin",
        "SOLVER_LEARNING_APPLY_CAPABILITY",
        "apply_solver_learning",
    ])
    require(root / "src/aasm/scoped_authority.py", [
        'SCOPED_AUTHORITY_CONTRACT_ID = "aasm.authority.scoped.v1"',
        '"deny_precedence": "ANY_MATCHING_DENY_OVERRIDES_ALLOW"',
        '"cross_run_authority_transfer": "NEVER"',
        '"default": "DENY"',
    ])
    require(root / "src/aasm/scoped_store.py", [
        'SCOPED_STORE_CONTRACT_ID = "aasm.store.scoped.v1"',
        '"raw_snapshot_access": "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY"',
        '"direct_store_write": "FORBIDDEN_USE_GOVERNED_RUNTIME_TRANSITIONS"',
    ])
    require(root / "src/aasm/solver_learning.py", [
        'SOLVER_LEARNING_CONTRACT_ID = "aasm.solver.learning.v1"',
        'SOLVER_LEARNING_APPLICATION_CONTRACT_ID = "aasm.solver.learning.application.v1"',
        '"cross_run_authority_transfer": "NEVER"',
        '"pruning_application": "LOCAL_REVALIDATION_REQUIRED"',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
        "build_solver_learning_application",
        "apply_solver_learning_to_optimization_request",
    ])
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs", "add_hint"])

    # Frozen v0.52 parent remains independently valid and versioned.
    require(root / "src/aasm/public_v52.py", [
        '__version__ = "0.52.0"',
        '"contract_version": "0.28.0"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "MULTI_OBJECTIVE_CONTRACT_ID",
        "RESOURCE_ROUTING_CONTRACT_ID",
    ])
    require(root / "src/aasm/public_v51.py", [
        '__version__ = "0.51.0"',
        '"contract_version": "0.27.0"',
        "SOLUTION_POOL_CONTRACT_ID",
        "ENUMERATION_CONTRACT_ID",
    ])

    # Preserve proof, RC, cross-run and SII authority boundaries.
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        '"proof_certified_requires_independent_checker": True',
        '"certificate_authority": "EVIDENCE_ONLY"',
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
        "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
    ])
    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"',
        '"authority_transfer": "NEVER"',
        '"authority_inherited": False',
    ])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"',
        "REQUIRED_VERIFICATION_NEVER_REDUCED",
        '"authority_reward": "NEVER"',
    ])

    # Exact-SHA release gate now includes the two v0.53 statuses.
    require(root / ".github/workflows/release.yml", [
        "aasm/ci-summary",
        "aasm/formal-assurance",
        "aasm/semantic-solver-rc",
        "aasm/proof-claims",
        "aasm/solution-pools",
        "aasm/optimization",
        "aasm/scoped-authority",
        "aasm/solver-learning",
        "Require exact main commit and all release gates",
    ])
    require(root / ".github/workflows/scoped-authority.yml", ["aasm/scoped-authority"])
    require(root / ".github/workflows/solver-learning.yml", ["aasm/solver-learning"])
    require(root / ".github/workflows/optimization.yml", ["aasm/optimization"])

    for name in (
        "scoped-principal.schema.json",
        "workspace.schema.json",
        "scoped-authority-grant.schema.json",
        "scoped-authority-decision.schema.json",
        "scoped-store-access.schema.json",
        "solver-learning-artifact.schema.json",
        "solver-learning-validation.schema.json",
        "solver-learning-application.schema.json",
        "multi-objective-problem.schema.json",
        "pareto-frontier.schema.json",
        "resource-capacity.schema.json",
        "resource-observation.schema.json",
        "resource-demand.schema.json",
        "solution-pool.schema.json",
        "enumeration-completeness-certificate.schema.json",
        "solver-claim-certificate.schema.json",
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

    subprocess.check_call([sys.executable, str(root / "scripts" / "check_v52_contracts.py")])
    subprocess.check_call([sys.executable, str(root / "scripts" / "check_v53_contracts.py")])
    subprocess.check_call([sys.executable, str(root / "scripts" / "check_v53_solver_learning_contracts.py")])

    require(root / "docs" / "CURRENT_RELEASE.md", ["v0.53.0", "0.29.0"])
    require(root / "docs" / "RELEASE_0.53.md", [
        "AASM v0.53.0",
        "Scoped Identity/Authority",
        "solver learning",
    ])

    print("v0.53.0 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
