from pathlib import Path
import os
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


def run_script(root: Path, name: str) -> None:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    subprocess.check_call([sys.executable, str(root / "scripts" / name)], cwd=root, env=env)


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    version = str(project["version"])
    if version != "0.56.0":
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

    # Active public release boundary.
    require(root / "src/aasm/__init__.py", ["public_v56"])
    require(root / "src/aasm/public_v56.py", [
        '__version__ = "0.56.0"',
        '"contract_version": "0.32.0"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "SOLVER_OUTCOME_V2_CONTRACT_ID",
        "SOLVER_STATUS_V2_CONTRACT_ID",
        "SOLVER_TERMINATION_V2_CONTRACT_ID",
        "SOLVER_EVIDENCE_GRADE_CONTRACT_ID",
        "PROVIDER_STATUS_MAP_CONTRACT_ID",
        "project_v2_to_legacy_status",
        "map_provider_status",
        "_demo_stack.AASMEngine = AASMEngine",
    ])
    require(root / "src/aasm/runtime_v56.py", ["AASMEngine"])
    require(root / "src/aasm/runtime_v56_foundation.py", ["SolverOutcomeV2RuntimeMixin", "V55FoundationEngine", "AASMEngine"])
    require(root / "src/aasm/solver_outcome_v2.py", [
        'SOLVER_OUTCOME_V2_CONTRACT_ID = "aasm.solver.outcome.v2"',
        'SOLVER_STATUS_V2_CONTRACT_ID = "aasm.solver.status.v2"',
        'SOLVER_TERMINATION_V2_CONTRACT_ID = "aasm.solver.termination.v2"',
        '"authoritative_detailed_status": "normalized_status"',
        '"incumbent_admission": "NONEMPTY_ASSIGNMENT_MUST_PASS_AASM_INDEPENDENT_MODEL_VALIDATION"',
        '"legacy_projection": "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED"',
        '"truth_authority": "NONE"',
        "MEMORY_LIMIT_WITH_INCUMBENT",
        "PROVIDER_UNAVAILABLE",
        "UNSUPPORTED_FEATURE",
        "STALE_RESULT",
    ])
    require(root / "src/aasm/provider_status_v2.py", [
        'PROVIDER_STATUS_MAP_CONTRACT_ID = "aasm.solver.provider-status-map.v1"',
        '"fuzzy_matching": "FORBIDDEN"',
        '"substring_inference": "FORBIDDEN"',
        "ortools_cp_sat_status_map",
        "highs_status_map",
        "pysat_cadical_status_map",
    ])
    require(root / "src/aasm/_runtime_v56_solver_outcome.py", [
        'SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID = "aasm.solver.outcome-v2.runtime.v1"',
        '"parallel_result_table": "NONE"',
        '"incumbent_validation": "AASM_VALIDATE_OPTIMIZATION_SOLUTION_BEFORE_ACCEPTANCE"',
        '"truth_authority": "NONE"',
    ])

    # Released v0.55 parent remains intact.
    require(root / "src/aasm/public_v55.py", [
        '__version__ = "0.55.0"',
        '"contract_version": "0.31.0"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "EXTERNAL_REFERENCE_CONTRACT_ID",
        "PROBLEM_REVISION_CONTRACT_ID",
        "PROBLEM_DELTA_CONTRACT_ID",
        "SOLVER_FORMULATION_CONTRACT_ID",
        "DiscreteBooleanModel",
        "SchedulingModel",
        "ContinuousModel",
        "GovernedDecisionVector",
        "SemanticEvolutionArchive",
    ])
    require(root / "src/aasm/semantic_evolution.py", [
        'EXTERNAL_REFERENCE_CONTRACT_ID = "aasm.external.reference.v1"',
        'PROBLEM_REVISION_CONTRACT_ID = "aasm.problem.revision.v1"',
        'PROBLEM_DELTA_CONTRACT_ID = "aasm.problem.delta.v1"',
    ])
    require(root / "src/aasm/model_features.py", [
        'MODEL_FEATURE_SET_CONTRACT_ID = "aasm.model.feature-set.v1"',
        'PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID = "aasm.provider.capability-manifest.v1"',
        'MODEL_ADMISSION_CONTRACT_ID = "aasm.model.admission.v1"',
    ])
    require(root / "src/aasm/solver_formulation.py", [
        'SOLVER_FORMULATION_CONTRACT_ID = "aasm.solver.formulation.v1"',
        '"nontrivial_translation_policy": "NO_PASS_WITHOUT_AN_INDEPENDENT_CHECKER_FOR_THE_REQUESTED_FIDELITY"',
        "verify_solver_formulation_identity",
    ])
    require(root / "src/aasm/discrete_ir.py", [
        "PseudoBooleanConstraint",
        "CardinalityConstraint",
        "verify_discrete_boolean_linearization",
        '"approximation": "NOT_SUPPORTED_BY_THIS_CONTRACT"',
    ])
    require(root / "src/aasm/scheduling_ir.py", [
        "CumulativeResourceConstraint",
        "validate_scheduling_assignment",
        '"execution_adapter": "NOT_CLAIMED_BY_THIS_FOUNDATION"',
    ])
    require(root / "src/aasm/continuous_ir.py", [
        "NumericTolerancePolicy",
        "QuadraticConstraint",
        "SecondOrderConeConstraint",
        '"optimality_proof": "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION"',
    ])
    require(root / "src/aasm/decision_vector_ir.py", [
        "DecisionHardFloor",
        "GovernedDecisionVector",
        '"scalarization": "NONE"',
    ])
    require(root / "src/aasm/semantic_archive.py", [
        "SemanticEvolutionArchive",
        '"replay": "EXISTING_AASM_REDUCER_OVER_ARCHIVED_EVENTS"',
        '"event_sequence_semantics": "DURABLE_ORDERING_ONLY_NOT_MACHINE_VERSION"',
        '"replay_uses_persisted_snapshot": False',
    ])

    # Earlier parent surfaces remain intact and independently checked.
    require(root / "src/aasm/public_v54.py", ['__version__ = "0.54.0"', '"contract_version": "0.30.0"'])
    require(root / "src/aasm/public_v53.py", ['__version__ = "0.53.0"', '"contract_version": "0.29.0"'])
    require(root / "src/aasm/public_v52.py", ['__version__ = "0.52.0"', '"contract_version": "0.28.0"'])
    require(root / "src/aasm/public_v51.py", ['__version__ = "0.51.0"', '"contract_version": "0.27.0"'])

    # Existing solver/resource/authority boundaries remain present.
    require(root / "src/aasm/runtime_v54.py", [
        'SOLVER_TRANSLATION_CONTRACT_ID = "aasm.solver.translation.v1"',
        'SOLVER_PORTFOLIO_CONTRACT_ID = "aasm.solver.portfolio.v1"',
        '"fastest_result": "NEVER_CORRECTNESS_TIEBREAK"',
        '"unknown_outcome": "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION"',
    ])
    require(root / "src/aasm/scoped_authority.py", [
        'SCOPED_AUTHORITY_CONTRACT_ID = "aasm.authority.scoped.v1"',
        '"deny_precedence": "ANY_MATCHING_DENY_OVERRIDES_ALLOW"',
        '"default": "DENY"',
    ])
    require(root / "src/aasm/solver_learning.py", [
        'SOLVER_LEARNING_CONTRACT_ID = "aasm.solver.learning.v1"',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
    ])
    require(root / "src/aasm/proof_claims.py", [
        'SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"',
        '"proof_certified_requires_independent_checker": True',
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
        "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
    ])

    # Schemas shipped in the current/parent release family.
    for name in (
        "external-reference.schema.json",
        "problem-revision.schema.json",
        "problem-delta.schema.json",
        "model-feature-set.schema.json",
        "provider-capability-manifest.schema.json",
        "model-admission-report.schema.json",
        "solver-formulation.schema.json",
        "solver-formulation-certificate.schema.json",
        "discrete-boolean-model.schema.json",
        "discrete-linearization.schema.json",
        "scheduling-model.schema.json",
        "scheduling-validation.schema.json",
        "continuous-model.schema.json",
        "continuous-validation.schema.json",
        "decision-vector.schema.json",
        "semantic-evolution-archive.schema.json",
        "solver-outcome-v2.schema.json",
        "provider-status-map.schema.json",
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

    # Preserve all earlier release-specific contract gates and the current v0.56 gate.
    for script in (
        "check_v52_contracts.py",
        "check_v53_contracts.py",
        "check_v53_solver_learning_contracts.py",
        "check_v54_contracts.py",
        "check_v55_discrete_ir.py",
        "check_v55_scheduling_ir.py",
        "check_v55_continuous_ir.py",
        "check_v55_decision_vector.py",
        "check_v55_semantic_archive.py",
        "check_v56_solver_outcome.py",
    ):
        run_script(root, script)

    require(root / "README.md", [
        "Current release — v0.56.0",
        "aasm.adoption.v1 / 0.32.0",
        "v0.56.1 — Execution Profiles + Runtime Provenance",
    ])
    require(root / "docs" / "CURRENT_RELEASE.md", [
        "AASM v0.56.0",
        "0.32.0",
        "public_v56",
        "aasm.solver.outcome.v2",
        "Truthful Solver Outcomes",
    ])
    require(root / "docs" / "RELEASE_0.56.md", [
        "AASM v0.56.0",
        "Normalized Solver Outcome v2",
        "CaDiCaL",
        "v0.56.1",
    ])
    require(root / ".github/workflows/v56.yml", [
        "AASM v0.56 Release",
        "ACTIVE_DEVELOPMENT",
        "active public v0.56 release contract: PASS",
        "context='aasm/v56'",
    ])
    require(root / ".github/workflows/release.yml", [
        "aasm/v54 aasm/v55 aasm/v56",
        "verify-github-release",
        "--notes-file docs/CURRENT_RELEASE.md",
    ])

    print("v0.56.0 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
