from __future__ import annotations

import json
from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing v0.53 solver-learning contract tokens {missing}")


def schema(root: Path, name: str) -> dict:
    path = root / "schemas" / name
    if not path.exists():
        raise SystemExit(f"missing v0.53 solver-learning schema: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not str(data.get("$schema", "")).startswith("https://json-schema.org/"):
        raise SystemExit(f"invalid schema declaration: {name}")
    return data


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    require(root / "src/aasm/solver_learning.py", [
        'SOLVER_LEARNING_CONTRACT_ID = "aasm.solver.learning.v1"',
        'SOLVER_LEARNING_CHECKER_ID = "aasm.checker.solver-learning-finite.v1"',
        'SOLVER_LEARNING_APPLICATION_CONTRACT_ID = "aasm.solver.learning.application.v1"',
        '"NO_GOOD"', '"UNSAT_CORE"', '"BOUND"',
        '"INCUMBENT"', '"WARM_START"', '"NATIVE_ACCELERATOR"',
        '"cross_run_transport": "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE"',
        '"cross_run_authority_transfer": "NEVER"',
        '"cross_run_admission_implies_truth": False',
        '"pruning_application": "LOCAL_REVALIDATION_REQUIRED"',
        '"performance_hint_authority": "NEVER_TRUTH_OR_POLICY"',
        '"model_compatibility": "EXACT_MODEL_FINGERPRINT"',
        '"application": "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY"',
        '"application_truth_authority": "NONE"',
        '"application_policy_authority": "NONE"',
        '"solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"',
        '"validation_required": "PASS_EXACT_ARTIFACT_AND_MODEL"',
        '"pruning_lowering": "NEW_OPTIMIZATION_MODEL_EXISTING_PROVIDER_PATH"',
        '"performance_lowering": "EXPLICIT_PROVIDER_CONSUMED_HINT_ONLY"',
        "class SolverLearningApplication:",
        "_validate_learning_literal_domain",
        "UNKNOWN_LITERAL_VARIABLE",
        "NON_BOOLEAN_LITERAL_VARIABLE",
        "build_solver_learning_application",
        "apply_solver_learning_to_optimization_request",
        "certify_complete_finite_enumeration",
        "LEARNED_PRUNING_WOULD_EXCLUDE_FEASIBLE_SOLUTIONS",
        "LEARNED_BOUND_FALSE_FOR_EXACT_MODEL",
        '"PERFORMANCE_HINT_ONLY"',
        '"PRUNING_CERTIFIED_FOR_EXACT_MODEL"',
    ])

    require(root / "src/aasm/_runtime_v53_solver_learning.py", [
        'SOLVER_LEARNING_RUNTIME_CONTRACT_ID = "aasm.solver.learning.runtime.v1"',
        '"export": "solver.learning.export"',
        '"import": "solver.learning.import"',
        '"validate": "solver.learning.validate"',
        '"apply": "solver.learning.apply"',
        '"cross_run_transport": "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE"',
        '"cross_run_admission": "EXISTING_AASM_V48_ADMISSION_REQUIRED"',
        '"cross_run_authority_transfer": "NEVER"',
        '"imported_pruning_state": "INERT_UNTIL_RECEIVING_RUN_LOCAL_REVALIDATION"',
        '"application": "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY"',
        '"apply_authority": "SCOPED_SOLVER_LEARNING_APPLY_REQUIRED"',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
        '"solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"',
        'knowledge_kind="REUSE_RESULT"',
        '"solver_learning_contract_id": SOLVER_LEARNING_CONTRACT_ID',
        '"solver_learning_contract_version": SOLVER_LEARNING_CONTRACT_VERSION',
        '"authority_transfer": "NEVER"',
        "revalidate_solver_learning",
        '"authority_inherited": False',
        '"truth_authority": "NONE"',
        '"cross_run_admission_implied_truth": False',
    ])

    require(root / "src/aasm/runtime_v53_learning.py", [
        "class AASMEngine(SolverLearningRuntimeMixin, V53AuthorityEngine)",
        'SOLVER_LEARNING_APPLY_CAPABILITY = "solver.learning.apply"',
        'report.get("envelopes", {}).get(envelope_id)',
        'admission.get("status") != "ACTIVE"',
        "cross_run_knowledge_report()",
        "admit_cross_run_solver_learning",
        "_latest_solver_learning_validation",
        "apply_solver_learning",
        '"solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"',
        '"executed": False',
        '"cross_run_admission_evidence_id": admission_evidence_id',
        '"authority_inherited": False',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
    ])

    require(root / "src/aasm/optimization.py", [
        'hints = request.metadata.get("solver_learning_hints") or []',
        'model.add_hint(variables[str(variable_id)], self._integer(float(value)))',
        '"solver_learning_hint_count": len(consumed_learning_applications)',
        '"solver_learning_application_ids": list(consumed_learning_applications)',
        '"solver_learning_hints_consumed": len(consumed_learning_applications)',
    ])

    artifact_schema = schema(root, "solver-learning-artifact.schema.json")
    validation_schema = schema(root, "solver-learning-validation.schema.json")
    kinds = set(artifact_schema["properties"]["learning_kind"]["enum"])
    expected_kinds = {"NO_GOOD", "UNSAT_CORE", "BOUND", "INCUMBENT", "WARM_START", "NATIVE_ACCELERATOR"}
    if kinds != expected_kinds:
        raise SystemExit(f"solver-learning kind schema drift: {sorted(kinds)}")
    if validation_schema["properties"]["checker_id"].get("const") != "aasm.checker.solver-learning-finite.v1":
        raise SystemExit("solver-learning validation checker identity drift")

    require(root / "src/aasm/cross_run_knowledge.py", [
        "def propose_cross_run_admission(self, envelope, *, proposer_id: str",
        "def commit_cross_run_admission(self, decision_id: str, *, worker_id: str)",
        '"envelopes": deepcopy(dict(sorted(envelopes.items())))',
        '"authority_transfer": "NEVER"',
        '"authority_inherited": False',
    ])

    require(root / "tests/test_v53_solver_learning.py", [
        "test_exact_finite_no_good_revalidation_accepts_only_truly_infeasible_conjunction",
        "test_no_good_revalidation_rejects_unknown_and_non_boolean_literal_variables_before_enumeration",
        "test_certified_boolean_no_good_lowers_to_existing_cp_sat_model_ir",
        "test_certified_sat_no_good_lowers_to_complement_clause",
        "test_certified_bound_application_preserves_validation_tolerance",
        "test_failed_validation_cannot_be_turned_into_application",
        "test_validated_assignment_hint_is_packaged_only_for_explicit_ortools_adapter",
        "test_native_accelerator_requires_exact_backend_version_and_environment_and_stays_performance_only",
    ])
    require(root / "tests/test_runtime_v53_solver_learning.py", [
        'proposer_id="solver-learning-importer"',
        'worker_id="solver-learning-admission-worker"',
        "test_cross_run_solver_learning_reuses_v48_transport_and_stays_inert_until_local_validation",
        "test_cross_run_solver_learning_cannot_materialize_before_v48_admission_commits",
        "test_cross_run_import_requires_local_scoped_import_authority_after_v48_admission",
        "test_forged_cross_run_no_good_may_be_admitted_as_evidence_but_local_revalidation_fails",
        "test_validated_learning_remains_inert_without_scoped_apply_authority",
        "test_scoped_apply_builds_durable_existing_path_request_without_executing",
    ])
    require(root / "tests/test_v44_optimization_real.py", [
        "test_real_ortools_consumes_validated_solver_learning_assignment_hint",
        'result.metadata["solver_learning_hints_consumed"] == 1',
    ])

    print("v0.53 solver learning contract check: PASS")


if __name__ == "__main__":
    main()
