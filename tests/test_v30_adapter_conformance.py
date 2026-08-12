from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

import jsonschema
import pytest

from aasm import AASMEngine
from aasm.effects import EffectRecord, EffectSpec
from aasm.integrations.conformance import (
    ADAPTER_CONFORMANCE_ID,
    ADAPTER_CONFORMANCE_VERSION,
    CONFORMANCE_SCENARIOS,
    AdapterCapabilityDeclaration,
    AdapterConformanceKit,
    ConformanceStatus,
)
from aasm.integrations.conformance_registry import (
    list_conformance_drivers,
    run_adapter_conformance,
)
from aasm.integrations.langgraph_conformance import LangGraphConformanceDriver


ROOT = Path(__file__).resolve().parents[1]


def test_langgraph_reference_driver_passes_all_required_scenarios():
    report = run_adapter_conformance("langgraph")
    assert report.status == ConformanceStatus.PASS.value
    assert report.valid is True
    assert report.contract_id == ADAPTER_CONFORMANCE_ID
    assert report.contract_version == ADAPTER_CONFORMANCE_VERSION
    assert report.coverage["passed"] == list(CONFORMANCE_SCENARIOS)
    assert report.coverage["failed"] == []
    assert report.coverage["inconclusive"] == []
    assert report.audit["total_violations"] == 0
    assert len(report.report_fingerprint) == 64
    assert all(result.valid for result in report.scenarios)
    assert all(
        result.replay_snapshot_hash == result.persisted_snapshot_hash
        for result in report.scenarios
    )


def test_conformance_report_and_capability_declaration_validate_against_schemas():
    report = run_adapter_conformance("langgraph", scenarios=["success"]).to_dict()
    capability_schema = json.loads(
        (ROOT / "schemas" / "adapter-capability.schema.json").read_text()
    )
    report_schema = json.loads(
        (ROOT / "schemas" / "adapter-conformance-report.schema.json").read_text()
    )
    jsonschema.validate(report["adapter"], capability_schema)
    from referencing import Registry, Resource

    registry = Registry().with_resource(
        capability_schema["$id"], Resource.from_contents(capability_schema)
    )
    jsonschema.Draft202012Validator(report_schema, registry=registry).validate(report)


def test_direct_storage_write_is_rejected_even_when_functional_output_passes():
    class DirectWriteDriver(LangGraphConformanceDriver):
        def run_scenario(self, scenario_id, context):
            outcome = super().run_scenario(scenario_id, context)
            context.store.save_effect(
                EffectRecord(
                    outcome.machine_id,
                    EffectSpec(
                        "broken.direct-write",
                        idempotency_key="broken-direct-write",
                    ),
                )
            )
            return outcome

    report = AdapterConformanceKit().run(
        DirectWriteDriver(), scenarios=["success"]
    )
    assert report.status == "FAIL"
    result = report.scenarios[0]
    assert result.checks["original_output_preserved"] is True
    assert result.checks["no_direct_storage_write"] is False
    assert "DIRECT_STORAGE_WRITE" in {finding.code for finding in result.findings}
    assert report.audit["total_violations"] == 1


def test_duplicate_machine_authority_declaration_is_rejected():
    class DuplicateAuthorityDriver(LangGraphConformanceDriver):
        def capability_declaration(self):
            declaration = super().capability_declaration()
            declaration.authority = {
                **declaration.authority,
                "machine_truth_authority": "LANGGRAPH_CHECKPOINT",
                "duplicate_authorities": ["FRAMEWORK_MACHINE_TRUTH"],
            }
            return declaration

    report = AdapterConformanceKit().run(
        DuplicateAuthorityDriver(), scenarios=["success"]
    )
    assert report.status == "FAIL"
    result = report.scenarios[0]
    assert result.checks["machine_truth_is_aasm_event_history"] is False
    assert result.checks["no_declared_duplicate_authorities"] is False
    assert "DUPLICATE_OR_BYPASSED_AUTHORITY" in {
        finding.code for finding in result.findings
    }


def test_unsupported_required_scenario_is_inconclusive_not_silently_passed():
    class PartialDriver(LangGraphConformanceDriver):
        def capability_declaration(self):
            declaration = super().capability_declaration()
            declaration.scenarios["lease_loss"] = False
            return declaration

        def run_scenario(self, scenario_id, context):  # pragma: no cover
            raise AssertionError("unsupported scenario must not execute")

    report = AdapterConformanceKit().run(
        PartialDriver(), scenarios=["lease_loss"]
    )
    assert report.status == "INCONCLUSIVE"
    result = report.scenarios[0]
    assert result.status == "INCONCLUSIVE"
    assert result.checks["scenario_supported"] is None
    assert result.findings[0].code == "SCENARIO_UNSUPPORTED"


def test_persisted_snapshot_tampering_produces_replay_or_history_failure():
    class TamperingDriver(LangGraphConformanceDriver):
        def run_scenario(self, scenario_id, context):
            outcome = super().run_scenario(scenario_id, context)
            raw = context.store.raw_store
            raw._snapshots[outcome.machine_id].metadata["framework_private_truth"] = {
                "claimed_complete": True
            }
            return outcome

    report = AdapterConformanceKit().run(
        TamperingDriver(), scenarios=["success"]
    )
    assert report.status == "FAIL"
    result = report.scenarios[0]
    codes = {finding.code for finding in result.findings}
    assert {"REPLAY_MISMATCH", "DURABLE_HISTORY_INVALID"} & codes
    assert result.checks["replay_exact"] is False or result.checks["durable_history_valid"] is False


def test_driver_registry_is_machine_readable_and_aliases_langgraph():
    rows = list_conformance_drivers()
    assert len(rows) == 1
    row = rows[0]
    assert row["adapter_id"] == "aasm.langgraph.v1"
    assert set(row["aliases"]) == {"aasm.langgraph.v1", "langgraph"}
    assert all(row["scenarios"].values())


def test_cli_runs_subset_writes_report_and_lists_drivers(tmp_path, capsys):
    from aasm.cli import build_parser, main as cli_main

    parser = build_parser()
    args = parser.parse_args(
        ["adapter-conformance", "--adapter", "langgraph", "--scenario", "success"]
    )
    assert args.command == "adapter-conformance"
    output = tmp_path / "conformance.json"
    assert cli_main(
        [
            "adapter-conformance",
            "--adapter",
            "langgraph",
            "--scenario",
            "success",
            "--output",
            str(output),
        ]
    ) is None
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["coverage"]["selected_scenarios"] == ["success"]
    assert json.loads(output.read_text()) == payload

    assert cli_main(["adapter-conformance-list"]) is None
    listing = json.loads(capsys.readouterr().out)
    assert listing["contract_id"] == ADAPTER_CONFORMANCE_ID
    assert listing["drivers"][0]["adapter_id"] == "aasm.langgraph.v1"


def test_authenticated_http_runner_and_contract_endpoint(tmp_path):
    from aasm.server import make_handler

    database = tmp_path / "conformance.db"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), make_handler(str(database), "secret")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/adapter-conformance",
            headers={"Authorization": "Bearer secret"},
        )
        with urlopen(request, timeout=15) as response:
            contract = json.load(response)
        assert contract["contract_id"] == ADAPTER_CONFORMANCE_ID
        assert contract["drivers"][0]["adapter_id"] == "aasm.langgraph.v1"

        request = Request(
            f"http://127.0.0.1:{server.server_port}/v1/conformance/adapters/langgraph?scenario=success",
            headers={"Authorization": "Bearer secret"},
        )
        with urlopen(request, timeout=30) as response:
            report = json.load(response)
        assert report["status"] == "PASS"
        assert report["coverage"]["selected_scenarios"] == ["success"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_runtime_and_control_center_expose_conformance_without_new_authority():
    from aasm import ProblemSpec
    from aasm.control_center import html_document

    engine = AASMEngine(ProblemSpec("Inspect adapter conformance contract"))
    contract = engine.inspect_machine("adapter-conformance")
    assert contract["contract_id"] == ADAPTER_CONFORMANCE_ID
    html = html_document()
    for token in [
        "v0.30 Adapter Conformance Kit",
        "Run LangGraph conformance",
        "/v1/conformance/adapters/",
        "CONFORMANCE_HOOK_NOT_SANDBOX",
    ]:
        assert token in html
