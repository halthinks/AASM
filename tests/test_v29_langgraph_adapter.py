from __future__ import annotations

import asyncio
import importlib.util
import inspect

import pytest

from aasm import AASMEngine, DecisionRecord, MemoryStore
from aasm.runtime_v52 import AASMEngine as V52Engine
from aasm.integrations.langgraph import (
    LANGGRAPH_ADAPTER_ID,
    LANGGRAPH_ADAPTER_VERSION,
    LangGraphAdapter,
    LangGraphNodePolicy,
    LangGraphRecoveryAction,
    LangGraphRunKey,
)


def config(thread_id: str = "thread-1", **extra):
    return {"configurable": {"thread_id": thread_id, **extra}}


def test_thread_binding_is_deterministic_idempotent_and_authoritative():
    store = MemoryStore()
    adapter = LangGraphAdapter(store=store, namespace="tests")
    first_engine, first = adapter.bind(config())
    second_engine, second = adapter.bind(config())

    assert first.machine_id == second.machine_id
    assert first.created is True
    assert second.created is False
    assert first.machine_id == LangGraphRunKey(
        "tests", "thread-1"
    ).machine_id

    events = store.load_events(first.machine_id)
    assert [event.event_type for event in events].count("langgraph_run_bound") == 1
    report = adapter.integration_report(second_engine)
    assert report["machine_truth_authority"] == "AASM_EVENT_HISTORY"
    assert report["checkpoint_state_authority"] == "LANGGRAPH"
    assert report["direct_storage_mutation"] is False
    assert report["replay_snapshot_hash"] == report["persisted_snapshot_hash"]


def test_run_scoped_binding_requires_and_uses_run_id():
    adapter = LangGraphAdapter(namespace="tests", binding_scope="RUN")
    with pytest.raises(ValueError, match="requires a run_id"):
        adapter.bind(config())
    one = adapter.bind(config(run_id="run-a"))[1]
    two = adapter.bind(config(run_id="run-b"))[1]
    assert one.machine_id != two.machine_id


def test_binding_rejects_collision_with_non_adapter_machine():
    store = MemoryStore()
    key = LangGraphRunKey("tests", "thread-1")
    AASMEngine(
        problem=__import__("aasm").ProblemSpec("not an adapter machine"),
        store=store,
        machine_id=key.machine_id,
    )
    adapter = LangGraphAdapter(store=store, namespace="tests")
    with pytest.raises(ValueError, match="was not created"):
        adapter.bind(config())


def test_wrapped_node_preserves_result_and_records_obligation_evidence_and_route():
    store = MemoryStore()
    adapter = LangGraphAdapter(store=store, namespace="tests")

    class Command:
        def __init__(self):
            self.graph = None
            self.update = {"count": 2}
            self.resume = None
            self.goto = "verify"

    result = Command()

    def node(state, config=None):
        assert config["configurable"]["thread_id"] == "thread-1"
        return result

    wrapped = adapter.wrap_node("build", node)
    signature = inspect.signature(wrapped)
    assert "config" in signature.parameters
    assert signature.parameters["config"].annotation is inspect.Parameter.empty
    assert wrapped({"count": 1}, config()) is result

    engine, _ = adapter.bind(config())
    report = engine.calculus_report()
    obligations = list(report["obligations"].values())
    assert len(obligations) == 1
    assert obligations[0]["status"] == "COMMITTED"
    assert obligations[0]["required_evidence_types"] == ["langgraph_node_output"]
    assert obligations[0]["evidence_ids"]

    integration = adapter.integration_report(engine)
    assert [row["event_type"] for row in integration["node_events"]] == [
        "langgraph_node_entered",
        "langgraph_node_succeeded",
    ]
    assert integration["route_events"][0]["goto"] == "verify"


def test_wrapped_node_failure_is_durable_and_exception_is_not_swallowed():
    adapter = LangGraphAdapter(namespace="tests")

    def fail(_state):
        raise RuntimeError("broken node")

    wrapped = adapter.wrap_node("broken", fail)
    with pytest.raises(RuntimeError, match="broken node"):
        wrapped({"value": 1}, config("failure-thread"))

    engine, _ = adapter.bind(config("failure-thread"))
    obligation = next(iter(engine.calculus_report()["obligations"].values()))
    assert obligation["status"] == "BLOCKED"
    assert adapter.integration_report(engine)["node_events"][-1]["event_type"] == (
        "langgraph_node_failed"
    )


def test_async_node_preserves_async_result():
    adapter = LangGraphAdapter(namespace="tests")

    async def node(state, runtime=None):
        await asyncio.sleep(0)
        return {"value": state["value"] + 1, "runtime_seen": runtime is not None}

    wrapped = adapter.wrap_node("async", node)
    output = asyncio.run(wrapped({"value": 4}, config("async-thread"), object()))
    assert output == {"value": 5, "runtime_seen": True}


def test_decision_mapping_conflict_learning_backjump_and_reuse_preserve_unrelated_work():
    adapter = LangGraphAdapter(namespace="tests")
    engine, _ = adapter.bind(config("conflict-thread"))

    root = adapter.record_decision(
        engine,
        decision_id="D-db",
        subject="database",
        value="postgres",
    )
    schema = adapter.record_decision(
        engine,
        decision_id="D-schema",
        subject="schema",
        value="v2",
        kind="DERIVED",
        parent_ids=[root["decision_id"]],
    )
    cache = adapter.record_decision(
        engine,
        decision_id="D-cache",
        subject="cache",
        value="memory",
    )
    obligation = adapter.record_obligation(
        engine,
        obligation_id="O-schema",
        statement="Verify schema v2",
        decision_dependencies=[schema["decision_id"]],
    )

    result = adapter.record_conflict(
        engine,
        statement="schema v2 violates compatibility",
        implicated_decision_ids=["D-schema"],
        observed_at_obligation_id=obligation["obligation_id"],
    )
    report = engine.calculus_report()
    assert result["recovery"]["backjump"]["pivot_decision_id"] == "D-db"
    assert report["decisions"]["D-schema"]["status"] == "INVALIDATED"
    assert report["decisions"]["D-db"]["status"] == "INVALIDATED"
    assert report["decisions"]["D-cache"]["status"] == "ACTIVE"
    assert report["constraints"][result["constraint_id"]]["strength"] == "HARD"

    adapter.record_decision(
        engine,
        decision_id="D-schema-repeat",
        subject="schema",
        value="v2",
        activate=False,
    )
    with pytest.raises(ValueError, match="violates learned hard constraints"):
        engine.activate_decision("D-schema-repeat")


def test_pre_effect_authorization_uses_existing_aasm_effect_ledger():
    # This is a v0.29 historical compatibility fixture for the pre-scoped
    # effect API.  Keep it on the latest compatible parent runtime; v0.53
    # scoped effect semantics are independently covered by v0.53 tests/gates.
    adapter = LangGraphAdapter(namespace="tests", engine_class=V52Engine)
    engine, _ = adapter.bind(config("effect-thread"))
    first = adapter.authorize_effect(
        engine,
        effect_type="send-email",
        payload={"recipient": "person@example.com"},
        idempotency_key="email-1",
    )
    second = adapter.authorize_effect(
        engine,
        effect_type="send-email",
        payload={"recipient": "person@example.com"},
        idempotency_key="email-1",
    )
    assert first.spec.effect_id == second.spec.effect_id
    assert second.status == "AUTHORIZED"
    assert len(engine.list_effects()) == 1


def test_recovery_directives_reuse_aasm_recovery_and_do_not_claim_pause_ownership():
    adapter = LangGraphAdapter(namespace="tests")
    engine, _ = adapter.bind(config("recovery-thread"))
    adapter.record_decision(engine, decision_id="D-temp", subject="mode", value="fast")

    restarted = adapter.recover(
        engine,
        LangGraphRecoveryAction.RESTART,
        reason="discard speculative assignment",
        target="choose_mode",
        update={"repair": True},
    )
    assert restarted.action == "RESTART"
    assert engine.calculus_report()["active_model"] == {}

    paused = adapter.recover(
        engine,
        LangGraphRecoveryAction.PAUSE,
        reason="human review required",
    )
    with pytest.raises(ValueError, match="interrupt"):
        paused.to_langgraph_command()


def test_public_adapter_module_has_no_mandatory_langgraph_import():
    # Core adapter tests run even when LangGraph is absent.
    assert LANGGRAPH_ADAPTER_ID == "aasm.langgraph.v1"
    assert LANGGRAPH_ADAPTER_VERSION == "0.1.0"


@pytest.mark.skipif(
    importlib.util.find_spec("langgraph") is None,
    reason="real LangGraph contract runs in the optional-dependency CI job",
)
def test_real_langgraph_stategraph_adopts_aasm_without_graph_rewrite():
    from typing_extensions import TypedDict
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        count: int

    store = MemoryStore()
    adapter = LangGraphAdapter(store=store, namespace="real-langgraph")

    def increment(state: State):
        return {"count": state["count"] + 1}

    graph = StateGraph(State)
    graph.add_node("increment", adapter.wrap_node("increment", increment))
    graph.add_edge(START, "increment")
    graph.add_edge("increment", END)
    app = graph.compile(checkpointer=InMemorySaver())

    output = app.invoke({"count": 0}, config("real-thread"))
    assert output["count"] == 1
    engine, _ = adapter.bind(config("real-thread"))
    report = adapter.integration_report(engine)
    assert report["checkpoint_state_authority"] == "LANGGRAPH"
    assert report["machine_truth_authority"] == "AASM_EVENT_HISTORY"
    assert report["node_events"][-1]["event_type"] == "langgraph_node_succeeded"


def test_runtime_cli_server_and_control_center_expose_langgraph_boundary(tmp_path, capsys):
    import json
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import Request, urlopen

    from aasm import SQLiteStore
    from aasm.cli import build_parser, main as cli_main
    from aasm.control_center import html_document
    from aasm.server import make_handler

    database = tmp_path / "langgraph.db"
    adapter = LangGraphAdapter(
        store=SQLiteStore(database), namespace="http", engine_class=AASMEngine
    )
    engine, binding = adapter.bind(config("http-thread"))
    machine_id = binding.machine_id
    adapter.store.close()

    parser = build_parser()
    parsed = parser.parse_args(
        ["inspect", machine_id, "--store", str(database), "--surface", "langgraph"]
    )
    assert parsed.surface == "langgraph"
    binding_args = parser.parse_args(
        [
            "langgraph-binding",
            "cli-thread",
            "--namespace",
            "cli",
            "--store",
            str(database),
        ]
    )
    assert binding_args.command == "langgraph-binding"

    cli_main(
        [
            "langgraph-binding",
            "cli-thread",
            "--namespace",
            "cli",
            "--store",
            str(database),
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["adapter_id"] == LANGGRAPH_ADAPTER_ID
    assert payload["machine_id"].startswith("lg_")

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), make_handler(str(database), "secret")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/v1/machines/{machine_id}/inspect/langgraph",
            headers={"Authorization": "Bearer secret"},
        )
        with urlopen(request, timeout=5) as response:
            report = json.load(response)
        assert report["binding"]["binding"]["thread_id"] == "http-thread"
        assert report["machine_truth_authority"] == "AASM_EVENT_HISTORY"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    html = html_document()
    for token in [
        "v0.29 Thin LangGraph Adapter",
        "Adapted run",
        "/inspect/langgraph",
        "LangGraph checkpoints · AASM truth",
    ]:
        assert token in html


def test_langgraph_schemas_accept_binding_and_recovery_reports():
    import json
    from pathlib import Path

    import jsonschema

    root = Path(__file__).resolve().parents[1]
    adapter = LangGraphAdapter(namespace="schema")
    engine, binding = adapter.bind(config("schema-thread"))
    binding_schema = json.loads(
        (root / "schemas" / "langgraph-binding.schema.json").read_text()
    )
    jsonschema.validate(binding.to_dict(), binding_schema)

    recovery = adapter.recover(
        engine,
        LangGraphRecoveryAction.CONTINUE,
        reason="continue fixture",
        update={"ok": True},
    )
    recovery_schema = json.loads(
        (root / "schemas" / "langgraph-recovery.schema.json").read_text()
    )
    jsonschema.validate(recovery.to_dict(), recovery_schema)
