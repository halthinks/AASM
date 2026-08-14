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
    if version != "0.49.0":
        raise SystemExit(f"unexpected release version: {version}")

    # Project-wide Apache-2.0 / PEP 639 packaging is a permanent release invariant.
    if project.get("license") != "Apache-2.0":
        raise SystemExit(f"unexpected active license: {project.get('license')}")
    if set(project.get("license-files", [])) != {"LICENSE", "NOTICE", "LICENSE_POLICY.md"}:
        raise SystemExit(f"unexpected license files: {project.get('license-files')}")
    legacy_license_classifiers = [value for value in project.get("classifiers", []) if value.startswith("License ::")]
    if legacy_license_classifiers:
        raise SystemExit(f"PEP 639 license expression must not be paired with legacy license classifiers: {legacy_license_classifiers}")
    require(root / "LICENSE", ["Apache License", "Version 2.0, January 2004", "Grant of Patent License", "END OF TERMS AND CONDITIONS"])
    require(root / "NOTICE", ["AASM", "Copyright 2026 AASM contributors"])
    require(root / "LICENSE_POLICY.md", [
        "all AASM source code, documentation, tags, commits, and release versions are offered under Apache-2.0",
        "including AASM versions that were first distributed under the MIT License",
        "Earlier MIT grants remain valid",
        "prior AASM versions are not designated MIT-only",
    ])
    require(root / "MANIFEST.in", ["LICENSE NOTICE LICENSE_POLICY.md pyproject.toml"])
    require(root / "CONTRIBUTING.md", ["Apache License, Version 2.0", "Apache-2.0", "NOTICE"])

    stale_license_policy = [
        "v0.47.1 is the first Apache-2.0 AASM release",
        "v0.47.0 release is not rewritten",
        "remains the original MIT-licensed distribution",
        "already-published `v0.47.0` artifact remains historically MIT licensed",
        "already-published `v0.47.0` release remains under the MIT License",
    ]
    for policy_doc in (
        root / "README.md", root / "ROADMAP.md", root / "CHANGELOG.md", root / "docs/CURRENT_RELEASE.md",
        root / "docs/RELEASE_0.47.1.md", root / "docs/RELEASE_0.48.1.md", root / "docs/RELEASE_0.49.md",
    ):
        forbid(policy_doc, stale_license_policy)

    # Current v0.49 public surface.
    require(root / "src/aasm/__init__.py", ["public_v49"])
    require(root / "src/aasm/cli.py", ["cli_v49"])
    require(root / "src/aasm/public_v49.py", [
        '__version__ = "0.49.0"', '"contract_version": "0.25.0"', "runtime_v49",
        "SEMANTIC_SOLVER_RC_CONTRACT_VERSION", "RELEASE_CANDIDATE",
        "THIN_V48_COMPOSITION_NO_NEW_KERNEL", "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
        "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS",
        "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
    ])
    require(root / "src/aasm/runtime_v49.py", ["SemanticSolverRCRuntimeMixin", "V48Engine"])
    require(root / "src/aasm/_runtime_v49_rc.py", [
        "semantic_solver_rc_contract_report", "semantic_solver_rc_freeze_manifest", "semantic_solver_rc_upgrade_report",
        "semantic_solver_rc_cross_backend_report", "semantic_solver_rc_benchmark_report",
        "semantic_solver_rc_claim_audit", "semantic_solver_rc_certify",
    ])
    require(root / "src/aasm/semantic_solver_rc.py", [
        'SEMANTIC_SOLVER_RC_CONTRACT_ID = "aasm.semantic.solver.rc.v1"',
        'SEMANTIC_SOLVER_RC_CONTRACT_VERSION = "0.1.0"',
        'SEMANTIC_SOLVER_RC_STABILITY = "RELEASE_CANDIDATE"',
        'SEMANTIC_SOLVER_RC_COMPATIBILITY_FLOOR = "v0.41"',
        '"runtime_extension": "THIN_V48_COMPOSITION_NO_NEW_KERNEL"',
        '"cross_backend_rule": "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE"',
        '"benchmark_policy": "MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM"',
        '"native_solver_claim": "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS"',
        '"claim_policy": "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE"',
        "run_upgrade_compatibility", "run_cross_backend_overlap_certification", "run_rc_benchmarks",
        "run_claim_gate_audit", "run_semantic_solver_rc_certification",
    ])
    require(root / "src/aasm/cli_v49.py", [
        "semantic-solver-rc-contract", "semantic-solver-rc-freeze", "semantic-solver-rc-upgrade",
        "semantic-solver-rc-cross-backend", "semantic-solver-rc-benchmark",
        "semantic-solver-rc-claim-audit", "semantic-solver-rc-certify",
    ])

    # Preserve v0.48 cross-run authority boundaries.
    require(root / "src/aasm/public_v48.py", ['"contract_version": "0.24.0"', "PROVENANCE_ONLY_NEVER_INHERITED", "LOCAL_AUTHORIZED_REASONING_REQUIRED", "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED"])
    require(root / "src/aasm/runtime_v48.py", ["CrossRunKnowledgeRuntimeMixin", "V47Engine", "cross_run_source_not_active", "propose_memory_forget", "does not match admitted stable principal mapping"])
    require(root / "src/aasm/cross_run_knowledge.py", [
        'CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"',
        'CROSS_RUN_ADMISSION_CONTRACT_ID = "aasm.knowledge.cross-run.admission.v1"',
        'CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID = "aasm.principal.cross-run-map.v1"',
        '"authority_transfer": "NEVER"', '"receiving_admission": "POLICY_OR_CONTROLLER_REQUIRED"',
        '"source_authority": "PROVENANCE_ONLY_NEVER_INHERITED"',
    ])
    require(root / "src/aasm/_runtime_v48_knowledge.py", [
        "propose_cross_run_admission", "authorize_cross_run_admission", "commit_cross_run_admission",
        "materialize_cross_run_knowledge", "register_cross_run_reuse_candidate", "apply_cross_run_signal",
        "map_cross_run_principal", "admit_cross_run_sii_reputation", "used_by_sii_resource_lease",
    ])
    require(root / "src/aasm/cross_run_conformance.py", ["run_cross_run_knowledge_conformance", "revocation_blocks_existing_reuse", "exact_replay"])
    require(root / "src/aasm/_runtime_v41_reuse_certify.py", ["admission_validator_id", "admission_validator_version", '"authority_inherited": False'])

    # Preserve v0.47 governed SII and certification.
    require(root / "src/aasm/public_v47.py", ['"contract_version": "0.23.0"', "GOVERNED_ENFORCED", "NEVER_REDUCED_BY_SII"])
    require(root / "src/aasm/runtime_v47.py", ["SIIGovernanceRuntimeMixin", "V46Engine"])
    require(root / "src/aasm/sii_governance.py", [
        'SII_GOVERNED_CONTRACT_VERSION = "0.3.0"', 'SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"',
        "REQUIRED_VERIFICATION_NEVER_REDUCED", '"authority_reward": "NEVER"',
    ])
    require(root / "src/aasm/_runtime_v47_sii.py", ["request_sii_advanced_optimization", "request_sii_formal_verification", "policy-required verification must use the ordinary formal path"])
    require(root / "src/aasm/certification_v47.py", ['CERTIFICATION_CONTRACT_VERSION = "0.2.0"', '"sii-preview": "sii-governance"', "mandatory-verification-not-reduced"])

    # Preserve native/modeling/formal pathways as first-class APIs.
    require(root / "src/aasm/advanced_optimization.py", ["aasm.optimization.advanced.v1", "SEARCH_STATE_NEVER_PROMOTES_TRUTH", "EPHEMERAL_PERFORMANCE_ONLY", "cadical-incremental", "ortools-cp-sat-scheduling", "highs-advanced", "cvxpy-advanced", "unsat_core", "warm_start", "affine_soc"])
    require(root / "src/aasm/advanced_execution.py", ["Kissat404", "pysat:kissat404"])
    require(root / "src/aasm/_runtime_v46_advanced.py", ["advanced result lease expired before result commit", "advanced result implementation does not match admitted provider", "EVIDENCE_ONLY"])
    require(root / "src/aasm/convex_optimization.py", ["aasm.optimization.convex.v1", "solver.convex", "cvxpy", "EVIDENCE_ONLY"])
    require(root / "src/aasm/pulp_adapter.py", ["aasm.adapter.pulp.v1", "TRANSLATION_ONLY", '"solver_execution": "NEVER"'])
    require(root / "src/aasm/optimization.py", ["cadical", "ortools-cp-sat", "highs", "PySATCadicalWorker", "ORToolsCPSATWorker", "HighsMILPWorker"])
    require(root / "src/aasm/formal_workers.py", ['provider == "z3"', 'provider == "cvc5"', 'provider == "vampire"', "lean4"])
    require(root / "src/aasm/reuse_model.py", ["aasm.reuse.v1", "OPTIMIZATION_RESULT"])

    # Public release/docs claims must agree with the RC contract and actual gates.
    require(root / "README.md", [
        "Current release — v0.49.0", "Semantic Solver Release Candidate",
        "aasm.adoption.v1 / 0.25.0", "aasm.semantic.solver.rc.v1 / 0.1.0", "aasm.remote.v1 / 0.19.0",
        "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS", "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE",
        "aasm/semantic-solver-rc", "Kissat", "CaDiCaL", "CP-SAT scheduling — OR-Tools", "HiGHS", "CVXPY", "PuLP",
        "Z3", "cvc5", "Vampire", "Lean 4", "Required verification is never reduced",
        "Apache License, Version 2.0", "LICENSE_POLICY.md", "v0.50.0",
    ])
    require(root / "ROADMAP.md", ["v0.49.0", "Semantic Solver Release Candidate", "v0.50.0", "Post-RC Stabilization"])
    require(root / "CHANGELOG.md", ["[0.49.0]", "Semantic Solver Release Candidate", "[0.48.1]", "Project-Wide Apache-2.0 Policy Correction"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.49.0", "runtime_v49", "0.25.0", "aasm.semantic.solver.rc.v1 / 0.1.0", "Apache-2.0", "aasm/semantic-solver-rc"])
    require(root / "docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md", [
        "aasm.semantic.solver.rc.v1 / 0.1.0", "v0.41 → v0.49", "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS",
        "NO PUBLIC CAPABILITY CLAIM WITHOUT A REPRODUCIBLE GATE", "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE",
    ])
    require(root / "docs/RELEASE_0.49.md", ["AASM v0.49.0", "0.25.0", "RELEASE_CANDIDATE", "aasm/semantic-solver-rc", "Apache-2.0"])
    require(root / "docs/RELEASE_0.48.1.md", ["Project-Wide Apache-2.0 Policy Correction", "LICENSE_POLICY.md", "prior AASM versions", "MIT permissions remain valid"])
    require(root / "docs/RELEASE_0.47.1.md", ["Project-wide relicensing declaration", "also offered under Apache-2.0", "MIT-only", "LICENSE_POLICY.md"])

    require(root / "tests/test_v49_rc.py", ["0.49.0", "0.25.0", "v41_memo_preserved", "v47_sii_policy_preserved", "v48_foreign_authority_still_not_inherited"])
    require(root / "tests/test_v49_rc_real.py", ["AASM_REQUIRE_RC_BACKENDS", "cp_sat_and_milp_objectives_agree", "observed_orchestration_overhead_ratio"])
    require(root / ".github/workflows/rc.yml", ["Semantic Solver RC", "AASM_REQUIRE_RC_BACKENDS", "semantic-solver-rc-certify --real", "aasm/semantic-solver-rc"])
    require(root / ".github/workflows/release.yml", ["aasm/ci-summary", "aasm/formal-assurance", "aasm/semantic-solver-rc", "Require exact main commit and all release gates"])
    require(root / ".github/workflows/cross-run.yml", ["Cross-Run Knowledge", "test_v48_cross_run_knowledge.py", "test_v48_cross_run_sii_mapping.py"])
    require(root / ".github/workflows/optimization.yml", ["AASM_REQUIRE_OPTIMIZATION_BACKENDS", "AASM_REQUIRE_MODELING_BACKENDS", "AASM_REQUIRE_ADVANCED_BACKENDS", "AASM_REQUIRE_SII_BACKENDS", "test_v47_sii_real.py"])

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
        "semantic-solver-rc-freeze-manifest.schema.json", "semantic-solver-rc-benchmark-report.schema.json", "semantic-solver-rc-certification-report.schema.json",
        "cross-run-knowledge-envelope.schema.json", "cross-run-knowledge-bundle.schema.json", "cross-run-admission-certificate.schema.json", "cross-run-principal-map.schema.json",
        "optimization-model.schema.json", "optimization-request.schema.json", "optimization-result.schema.json",
        "convex-optimization-model.schema.json", "convex-optimization-request.schema.json", "convex-optimization-result.schema.json",
        "advanced-optimization-problem.schema.json", "advanced-optimization-request.schema.json", "advanced-optimization-result.schema.json",
        "sii-principal-binding.schema.json", "sii-scoring-policy.schema.json", "sii-governed-resource-lease.schema.json",
        "reuse-request.schema.json", "reuse-certificate.schema.json", "certification-report.schema.json",
    ):
        require(root / "schemas" / name, ['"$schema"', "2020-12"])

    print("v0.49.0 release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
