#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} is missing required S5.2 experiment-runtime tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.2 experiment-runtime firewalls: {found}")


def main() -> None:
    runtime = "src/aasm/experiment_runtime.py"
    tests = "tests/test_experiment_runtime.py"
    workflow = ".github/workflows/experiment.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        runtime,
        "class ExperimentRuntimeMixin",
        "project_experiment_evidence",
        "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "EXISTING_AASM_SEMANTIC_EVOLUTION_ONLY",
        "STALE_EXPERIMENT_PROBLEM_REVISION",
        "STALE_EXPERIMENT_SUPPORT_EVIDENCE",
        "EXPERIMENT_SELECTION_DETERMINISTIC_RECOMPUTATION_MISMATCH",
        "\"experiment_execution\": \"NONE\"",
        "\"effect_dispatch\": \"NONE\"",
        "\"resource_reservation\": \"NONE\"",
        "\"problem_mutation\": \"NONE\"",
        "\"parallel_experiment_store\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        runtime,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "reserve_candidate_resources(",
        "commit_problem_revision_transition(",
        "class ExperimentStore",
        "class ExperimentExecutor",
    )
    require_tokens(
        tests,
        "test_stale_problem_revision_blocks_new_experiment_record",
        "test_invalidated_support_blocks_new_experiment_but_does_not_erase_history",
        "test_selection_is_recomputed_and_cannot_choose_lower_information_value_candidate",
        "test_stale_constraint_assessment_evidence_blocks_new_selection",
        "test_selection_record_never_reserves_resources_or_dispatches_effects",
    )
    require_tokens(
        workflow,
        "src/aasm/experiment_runtime.py",
        "scripts/check_experiment_runtime_contracts.py",
        "tests/test_experiment_runtime.py",
    )
    if "experiment_runtime" in text(public):
        raise SystemExit("S5.2 experiment runtime must remain absent from the active public root")
    print("S5.2 durable governed experiment runtime contracts: PASS")


if __name__ == "__main__":
    main()
