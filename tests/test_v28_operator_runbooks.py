from __future__ import annotations

import json
from pathlib import Path
import pytest
from aasm import (
    MemoryStore, execute_operator_runbook, list_operator_runbooks,
    distributed_recovery_contract, certify_distributed_recovery,
)
from aasm.cli import build_parser, main

RUNBOOK_IDS = {"lease-loss","requirement-change","learned-no-good","human-approval","replay-fork","unknown-effect","history-diagnosis"}

def test_operator_runbook_registry_is_complete_and_documented():
    rows=list_operator_runbooks(); assert {row["runbook_id"] for row in rows}==RUNBOOK_IDS
    root=Path(__file__).resolve().parents[1]
    for row in rows:
        path=root/row["document"]; assert path.is_file(),row
        text=path.read_text(encoding="utf-8"); assert row["title"] in text; assert f"aasm runbook {row['runbook_id']}" in text

@pytest.mark.parametrize("runbook_id",sorted(RUNBOOK_IDS))
def test_each_operator_runbook_is_an_executable_passing_drill(runbook_id):
    payload=execute_operator_runbook(runbook_id,store=MemoryStore()).to_dict()
    assert payload["status"]=="PASS",json.dumps(payload,indent=2,default=str); assert payload["valid"] is True


def test_distributed_recovery_certificate_exercises_all_declared_failures():
    contract=distributed_recovery_contract(); first=certify_distributed_recovery(); second=certify_distributed_recovery()
    assert contract["contract_id"]=="aasm.recovery.v1"
    assert first["status"]=="PASS",json.dumps(first,indent=2,default=str)
    assert [row["scenario"] for row in first["scenarios"]]==contract["scenarios"]
    assert all(row["status"]=="PASS" for row in first["scenarios"])
    assert first["report_sha256"]==second["report_sha256"]


def test_runbook_and_recovery_cli_are_visible(capsys):
    parser=build_parser(); assert parser.parse_args(["runbook","lease-loss"]).runbook_id=="lease-loss"
    assert "recovery-certify" in parser.format_help()
    main(["recovery-certify"]); report=json.loads(capsys.readouterr().out); assert report["status"]=="PASS"
