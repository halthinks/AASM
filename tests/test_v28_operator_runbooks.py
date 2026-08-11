from __future__ import annotations

import json
from pathlib import Path

import pytest

from aasm import (
    MemoryStore,
    execute_operator_runbook,
    list_operator_runbooks,
)
from aasm.cli import build_parser, main


RUNBOOK_IDS = {
    "lease-loss",
    "requirement-change",
    "learned-no-good",
    "human-approval",
    "replay-fork",
    "unknown-effect",
    "history-diagnosis",
}


def test_operator_runbook_registry_is_complete_and_documented():
    rows = list_operator_runbooks()
    assert {row["runbook_id"] for row in rows} == RUNBOOK_IDS
    root = Path(__file__).resolve().parents[1]
    for row in rows:
        path = root / row["document"]
        assert path.is_file(), row
        text = path.read_text(encoding="utf-8")
        assert row["title"] in text
        assert f"aasm runbook {row['runbook_id']}" in text


@pytest.mark.parametrize("runbook_id", sorted(RUNBOOK_IDS))
def test_each_operator_runbook_is_an_executable_passing_drill(runbook_id):
    result = execute_operator_runbook(runbook_id, store=MemoryStore())
    payload = result.to_dict()
    assert payload["runbook_id"] == runbook_id
    assert payload["status"] == "PASS", json.dumps(payload, indent=2, default=str)
    assert payload["valid"] is True
    assert payload["machine_id"]
    assert payload["checks"]
    assert all(payload["checks"].values())


def test_operator_runbooks_expose_the_required_failure_boundaries():
    lease = execute_operator_runbook("lease-loss").to_dict()
    assert lease["checks"]["lost_lease_expired"] is True
    assert lease["checks"]["attempt_incremented"] is True

    requirement = execute_operator_runbook("requirement-change").to_dict()
    assert requirement["summary"]["affected_nodes"] == [
        "design-core",
        "update-tests",
    ]
    assert "publish-notes" in requirement["summary"]["unaffected_nodes"]

    learned = execute_operator_runbook("learned-no-good").to_dict()
    assert learned["checks"]["constraint_hard"] is True
    assert learned["checks"]["failed_model_blocked"] is True

    unknown = execute_operator_runbook("unknown-effect").to_dict()
    assert unknown["checks"]["unsafe_retry_blocked"] is True
    assert unknown["summary"]["final_status"] == "SUCCEEDED"

    diagnosis = execute_operator_runbook("history-diagnosis").to_dict()
    assert "NON_CONTIGUOUS_SEQUENCE" in diagnosis["summary"]["issue_codes"]
    assert diagnosis["checks"]["canonical_history_not_mutated"] is True


def test_runbook_cli_lists_and_executes_machine_readable_drills(capsys):
    parser = build_parser()
    parsed = parser.parse_args(["runbook", "lease-loss"])
    assert parsed.command == "runbook"
    assert parsed.runbook_id == "lease-loss"

    main(["runbook", "list"])
    listing = json.loads(capsys.readouterr().out)
    assert {row["runbook_id"] for row in listing["runbooks"]} == RUNBOOK_IDS

    main(["runbook", "history-diagnosis"])
    result = json.loads(capsys.readouterr().out)
    assert result["valid"] is True
    assert result["checks"]["sequence_gap_identified"] is True
