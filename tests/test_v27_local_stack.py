from __future__ import annotations

from pathlib import Path
import threading
from http.server import ThreadingHTTPServer

import pytest

from aasm import AASMEngine, SQLiteStore, __version__
from aasm.cli import build_parser
from aasm.control_center import html_document
from aasm.demo_stack import (
    bootstrap_stack,
    fresh_stack,
    read_stack_state,
    run_worker_cycle,
    stack_status,
    verify_stack,
)
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


@pytest.fixture(scope="module")
def seeded_stack(tmp_path_factory):
    root = tmp_path_factory.mktemp("v27-stack")
    database = root / "stack.db"
    state_path = root / "stack-state.json"
    state = bootstrap_stack(
        str(database),
        state_path=state_path,
        public_url="http://localhost:8787",
    )
    return root, database, state_path, state


def test_stack_bootstrap_seeds_live_and_completed_canonical_machines(seeded_stack):
    _root, database, state_path, state = seeded_stack
    assert state["runtime_version"] == __version__
    assert state["active_machine_id"] != state["completed_machine_id"]
    assert state["current_machine_id"] == state["active_machine_id"]
    assert Path(state_path).is_file()

    status = stack_status(str(database), state_path=state_path)
    assert status["machines"]["active"]["state"] == "SELECT"
    assert status["machines"]["completed"]["state"] == "COMPLETE"

    verified = verify_stack(
        str(database),
        state_path=state_path,
        selection="completed",
    )
    assert verified["valid"] is True
    assert verified["state"] == "COMPLETE"
    assert verified["replay_snapshot_hash"] == verified["persisted_snapshot_hash"]


def test_demo_worker_uses_existing_remote_registration_claim_and_lease_path(
    seeded_stack,
):
    _root, database, state_path, state = seeded_stack
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(str(database), "secret", demo_state_path=str(state_path)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        client = AASMRemoteClient(base_url, "secret")
        health = client.health()
        assert health["runtime_version"] == __version__
        stack = client._request("GET", "/demo-stack")
        assert stack["ready"] is True
        assert stack["active_machine_id"] == state["active_machine_id"]
        history = client._request(
            "GET",
            f"/v1/machines/{state['completed_machine_id']}/history-check",
        )
        assert history["valid"] is True
        assert history["reconstructed_snapshot_hash"] == history["persisted_snapshot_hash"]

        first = run_worker_cycle(
            state_path=state_path,
            base_url=base_url,
            token="secret",
            worker_id="demo-worker-1",
        )
        assert first["executed"] is True
        second = run_worker_cycle(
            state_path=state_path,
            base_url=base_url,
            token="secret",
            worker_id="demo-worker-1",
        )
        assert second["executed"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    store = SQLiteStore(database)
    try:
        engine = AASMEngine.resume(state["active_machine_id"], store)
        workers = {row["worker_id"]: row for row in engine.list_workers()}
        assert workers["demo-worker-1"]["status"] == "ACTIVE"
        leases = engine.list_leases()
        assert len(leases) == 1
        assert leases[0]["task_id"] == "demo-stack-provenance-probe"
        assert leases[0]["status"] == "COMPLETED"
        assert leases[0]["result"]["path"] == (
            "existing remote registration/claim/lease/completion API"
        )
    finally:
        store.close()


def test_fresh_is_a_non_destructive_canonical_reset(seeded_stack):
    _root, database, state_path, original = seeded_stack
    previous_machine = original["active_machine_id"]
    updated = fresh_stack(
        str(database),
        state_path=state_path,
        public_url="http://localhost:8787",
    )
    assert updated["active_machine_id"] != previous_machine
    assert updated["current_machine_id"] == updated["active_machine_id"]
    assert updated["generation"] == original["generation"] + 1

    store = SQLiteStore(database)
    try:
        assert store.load_snapshot(previous_machine).machine_id == previous_machine
        assert store.load_snapshot(updated["active_machine_id"]).state == "SELECT"
    finally:
        store.close()
    assert read_stack_state(state_path)["active_machine_id"] == updated["active_machine_id"]


def test_compose_and_control_center_expose_the_documented_stack_contract():
    root = Path(__file__).resolve().parents[1]
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    for token in [
        "postgres:17-alpine",
        "bootstrap:",
        "runtime:",
        "worker-1:",
        "worker-2:",
        "stackctl:",
        "service_completed_successfully",
        "aasm.demo_stack",
        "AASM_DEMO_STATE",
        "two-workers",
    ]:
        assert token in compose
    assert "DELETE FROM" not in compose
    assert "TRUNCATE" not in compose

    html = html_document()
    for token in [
        "v0.27 One-Command Local Full Stack",
        "Live setup machine",
        "Completed reference run",
        "/demo-stack",
        "aasmStackAutoload",
    ]:
        assert token in html

    parser = build_parser()
    stack_args = parser.parse_args(
        ["stack", "verify", "--store", "runs.db", "--selection", "completed"]
    )
    assert stack_args.command == "stack"
    assert stack_args.action == "verify"
    serve_args = parser.parse_args(
        [
            "serve",
            "--store",
            "runs.db",
            "--demo-state",
            "stack-state.json",
        ]
    )
    assert serve_args.demo_state == "stack-state.json"
