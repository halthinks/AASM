#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} is missing required S5.2 experiment tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.2 experiment firewalls: {found}")


def main() -> None:
    module = "src/aasm/experiment.py"
    tests = "tests/test_experiment_foundation.py"
    workflow = ".github/workflows/experiment.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        module,
        "EXPERIMENT_CONTRACT_ID = \"aasm.experiment.v1\"",
        "class ExperimentSpec",
        "class ExperimentSelectionCandidate",
        "class ExperimentSelectionProposal",
        "def propose_experiment_selection(",
        "HARD_REVISION_SAFETY_EVIDENCE_RESOURCE_GATE_BEFORE_INFORMATION_VALUE",
        "INTEGER_PARTS_PER_MILLION_NO_BINARY_FLOAT",
        "selection_is_proposal_only",
        "\"experiment_execution\": \"NONE\"",
        "\"effect_dispatch\": \"NONE\"",
        "\"resource_reservation\": \"NONE\"",
        "\"fact_authority\": \"NONE\"",
        "\"problem_mutation\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        module,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "authorize_effect(",
        "reserve_candidate_resources(",
        "commit_problem_revision_transition(",
        "class ExperimentStore",
        "eval(",
        "exec(",
    )
    require_tokens(
        tests,
        "test_selection_never_lets_information_gain_override_hard_constraint_gate",
        "test_no_eligible_experiment_produces_no_selection_not_a_fake_success",
        "test_fixture_and_calibration_must_be_bound_or_explicitly_not_applicable",
        "test_hard_context_references_cannot_be_silently_omitted",
        "test_selection_candidate_scores_are_integer_ppm_not_binary_float",
    )
    for schema in ("schemas/experiment.schema.json", "schemas/experiment-selection-proposal.schema.json"):
        json.loads(text(schema))
    require_tokens(
        workflow,
        "src/aasm/experiment.py",
        "scripts/check_experiment_contracts.py",
        "tests/test_experiment_foundation.py",
        "aasm/experiment",
    )
    if "experiment" in text(public):
        raise SystemExit("S5.2 experiment foundation must remain absent from the active public root")
    print("S5.2 governed experiment foundation contracts: PASS")


if __name__ == "__main__":
    main()
