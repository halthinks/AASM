from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

from .model import new_id
from .persistence.factory import open_store
from .remote import AASMRemoteClient
from .research_demo import run_research_synthesis_demo
from .resources import ResourceRecord, TaskDemand
from .runtime_v25 import AASMEngine
from .worker_loop import RemoteWorkerLoop
from .workers import WorkerRecord

DEFAULT_STATE_PATH = "/var/lib/aasm-demo/stack-state.json"
DEFAULT_PUBLIC_URL = "http://localhost:8787"
DEFAULT_INTERNAL_URL = "http://runtime:8787"
DEFAULT_WORKER_RESOURCE_ID = "aasm-demo-worker-pool"
STACK_SCHEMA_VERSION = 1


def _runtime_version() -> str:
    try:
        return importlib_metadata.version("aasm-runtime")
    except importlib_metadata.PackageNotFoundError:
        return "0.27.0"


def _json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str), flush=True)


@contextmanager
def _state_lock(state_path: Path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    handle = lock_path.open("a+")
    try:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        yield
    finally:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        handle.close()


def read_stack_state(state_path: str | Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    path = Path(state_path)
    if not path.exists():
        raise FileNotFoundError(f"AASM demo stack state does not exist: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != STACK_SCHEMA_VERSION:
        raise ValueError("invalid AASM demo stack state document")
    return value


def _write_stack_state(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)
    return deepcopy(value)


def _machine_exists(store, machine_id: str | None) -> bool:
    if not machine_id:
        return False
    try:
        store.load_snapshot(machine_id)
    except KeyError:
        return False
    return True


def _new_machine_id(kind: str) -> str:
    return new_id(f"demo-{kind}")


def _prepare_live_machine(engine: AASMEngine) -> None:
    if not any(
        row.get("resource_id") == DEFAULT_WORKER_RESOURCE_ID
        for row in engine.list_resources()
    ):
        engine.register_resource(
            ResourceRecord(
                DEFAULT_WORKER_RESOURCE_ID,
                "agent",
                ["aasm-demo", "reference-inspection"],
                capacity=2.0,
                reliability=1.0,
                metadata={
                    "demo_stack": True,
                    "purpose": "exercise the existing remote worker and lease path",
                },
            ),
            reason="v0.27 local stack worker resource registered",
        )
    tasks = [
        TaskDemand(
            "demo-stack-provenance-probe",
            ["aasm-demo"],
            demand=1.0,
            priority=100,
            allowed_kinds=["agent"],
            metadata={
                "demo_stack": True,
                "task_class": "reference-stack",
                "purpose": "prove remote registration, claim, lease, telemetry, and completion",
            },
        )
    ]
    engine.schedule(tasks, reason="v0.27 local stack worker task scheduled")


def _create_live_machine(store) -> tuple[str, dict[str, Any]]:
    machine_id = _new_machine_id("live")
    result = run_research_synthesis_demo(
        store=store,
        mode="setup",
        machine_id=machine_id,
    )
    _prepare_live_machine(result.engine)
    return machine_id, result.summary


def _create_completed_machine(store) -> tuple[str, dict[str, Any]]:
    machine_id = _new_machine_id("complete")
    result = run_research_synthesis_demo(
        store=store,
        mode="complete",
        machine_id=machine_id,
    )
    return machine_id, result.summary


def _base_state(
    *,
    existing: dict[str, Any] | None,
    active_machine_id: str,
    completed_machine_id: str,
    current_machine_id: str,
    public_url: str,
    generation: int,
) -> dict[str, Any]:
    now = time.time()
    created_at = (existing or {}).get("created_at", now)
    return {
        "schema_version": STACK_SCHEMA_VERSION,
        "runtime_version": _runtime_version(),
        "project_status": "EXPERIMENTAL",
        "reference_application": "research-synthesis",
        "store_kind": "postgresql-or-sqlite",
        "active_machine_id": active_machine_id,
        "completed_machine_id": completed_machine_id,
        "current_machine_id": current_machine_id,
        "generation": int(generation),
        "worker_resource_id": DEFAULT_WORKER_RESOURCE_ID,
        "expected_workers": ["demo-worker-1"],
        "optional_workers": ["demo-worker-2"],
        "control_center_url": public_url.rstrip("/") + "/",
        "health_url": public_url.rstrip("/") + "/health",
        "created_at": created_at,
        "updated_at": now,
        "reset_semantics": (
            "fresh creates a new canonical setup machine and preserves prior histories; "
            "docker compose down --volumes performs destructive storage reset"
        ),
    }


def bootstrap_stack(
    store_target: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    public_url: str = DEFAULT_PUBLIC_URL,
) -> dict[str, Any]:
    """Seed the live and completed reference machines through the public runtime path."""

    path = Path(state_path)
    with _state_lock(path):
        try:
            existing = read_stack_state(path)
        except FileNotFoundError:
            existing = None
        store = open_store(store_target)
        try:
            active_id = (existing or {}).get("active_machine_id")
            if not _machine_exists(store, active_id):
                active_id, _ = _create_live_machine(store)
            completed_id = (existing or {}).get("completed_machine_id")
            if not _machine_exists(store, completed_id):
                completed_id, _ = _create_completed_machine(store)
            current_id = (existing or {}).get("current_machine_id")
            if not _machine_exists(store, current_id):
                current_id = active_id
            generation = int((existing or {}).get("generation", 0) or 0)
            if generation < 1:
                generation = 1
            state = _base_state(
                existing=existing,
                active_machine_id=active_id,
                completed_machine_id=completed_id,
                current_machine_id=current_id,
                public_url=public_url,
                generation=generation,
            )
            _write_stack_state(path, state)
        finally:
            store.close()
    print("AASM one-command local stack seeded", flush=True)
    print(f"Control Center: {state['control_center_url']}", flush=True)
    print(f"Live setup machine: {state['active_machine_id']}", flush=True)
    print(f"Completed reference machine: {state['completed_machine_id']}", flush=True)
    return state


def fresh_stack(
    store_target: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    public_url: str = DEFAULT_PUBLIC_URL,
) -> dict[str, Any]:
    """Create a new setup machine without deleting prior durable history."""

    path = Path(state_path)
    with _state_lock(path):
        existing = read_stack_state(path)
        store = open_store(store_target)
        try:
            active_id, _ = _create_live_machine(store)
            completed_id = existing["completed_machine_id"]
            if not _machine_exists(store, completed_id):
                completed_id, _ = _create_completed_machine(store)
            state = _base_state(
                existing=existing,
                active_machine_id=active_id,
                completed_machine_id=completed_id,
                current_machine_id=active_id,
                public_url=public_url,
                generation=int(existing.get("generation", 0)) + 1,
            )
            _write_stack_state(path, state)
        finally:
            store.close()
    return state


def complete_stack(
    store_target: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    public_url: str = DEFAULT_PUBLIC_URL,
) -> dict[str, Any]:
    """Create and select a new completed reference trajectory."""

    path = Path(state_path)
    with _state_lock(path):
        existing = read_stack_state(path)
        store = open_store(store_target)
        try:
            completed_id, _ = _create_completed_machine(store)
            active_id = existing["active_machine_id"]
            if not _machine_exists(store, active_id):
                active_id, _ = _create_live_machine(store)
            state = _base_state(
                existing=existing,
                active_machine_id=active_id,
                completed_machine_id=completed_id,
                current_machine_id=completed_id,
                public_url=public_url,
                generation=int(existing.get("generation", 0)),
            )
            _write_stack_state(path, state)
        finally:
            store.close()
    return state


def select_stack_machine(
    selection: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    path = Path(state_path)
    with _state_lock(path):
        state = read_stack_state(path)
        if selection == "active":
            machine_id = state["active_machine_id"]
        elif selection == "completed":
            machine_id = state["completed_machine_id"]
        else:
            machine_id = selection
        state["current_machine_id"] = machine_id
        state["updated_at"] = time.time()
        _write_stack_state(path, state)
    return state


def stack_status(
    store_target: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    state = read_stack_state(state_path)
    store = open_store(store_target)
    try:
        machines: dict[str, Any] = {}
        for label, machine_id in [
            ("active", state.get("active_machine_id")),
            ("completed", state.get("completed_machine_id")),
            ("current", state.get("current_machine_id")),
        ]:
            if not machine_id:
                machines[label] = {"exists": False}
                continue
            try:
                snapshot = store.load_snapshot(machine_id)
            except KeyError:
                machines[label] = {"exists": False, "machine_id": machine_id}
                continue
            machines[label] = {
                "exists": True,
                "machine_id": machine_id,
                "state": snapshot.state,
                "version": snapshot.version,
                "workers": [
                    row.get("worker_id")
                    for row in snapshot.resources.get("workers", [])
                ],
                "leases": [
                    {
                        "task_id": row.get("task_id"),
                        "worker_id": row.get("worker_id"),
                        "status": row.get("status"),
                    }
                    for row in snapshot.resources.get("leases", [])
                ],
            }
    finally:
        store.close()
    return {"stack": state, "machines": machines}


def verify_stack(
    store_target: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    selection: str = "completed",
) -> dict[str, Any]:
    state = read_stack_state(state_path)
    machine_id = (
        state["completed_machine_id"]
        if selection == "completed"
        else state["active_machine_id"]
        if selection == "active"
        else state["current_machine_id"]
        if selection == "current"
        else selection
    )
    store = open_store(store_target)
    try:
        engine = AASMEngine.resume(machine_id, store)
        history = engine.check_durable_history(persist=False)
        replayed = engine.replay()
        replay_hash = replayed.canonical_hash()
        persisted_hash = engine.snapshot.canonical_hash()
        valid = bool(history.get("valid")) and replay_hash == persisted_hash
        return {
            "valid": valid,
            "machine_id": machine_id,
            "state": engine.state_value,
            "history_check": history,
            "replay_snapshot_hash": replay_hash,
            "persisted_snapshot_hash": persisted_hash,
        }
    finally:
        store.close()


def run_worker_cycle(
    *,
    state_path: str | Path,
    base_url: str,
    token: str | None,
    worker_id: str,
) -> dict[str, Any]:
    state = read_stack_state(state_path)
    machine_id = state["active_machine_id"]
    client = AASMRemoteClient(base_url, token, timeout=15.0)
    worker = WorkerRecord(
        worker_id,
        state.get("worker_resource_id", DEFAULT_WORKER_RESOURCE_ID),
        heartbeat_timeout=45.0,
        metadata={
            "demo_stack": True,
            "runtime_version": _runtime_version(),
            "executor": "deterministic-reference-worker",
        },
    )

    def executor(lease: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "worker_id": worker_id,
            "task_id": lease["task_id"],
            "lease_id": lease["lease_id"],
            "path": "existing remote registration/claim/lease/completion API",
            "artifact_refs": [],
        }

    loop = RemoteWorkerLoop(
        client,
        machine_id,
        worker,
        executor,
        lease_seconds=45.0,
        heartbeat_interval=10.0,
        idle_sleep=5.0,
    )
    executed = loop.run_once()
    return {
        "executed": executed,
        "machine_id": machine_id,
        "worker_id": worker_id,
    }


def worker_forever(
    *,
    state_path: str | Path,
    base_url: str,
    token: str | None,
    worker_id: str,
    idle_sleep: float = 10.0,
) -> None:
    while True:
        try:
            result = run_worker_cycle(
                state_path=state_path,
                base_url=base_url,
                token=token,
                worker_id=worker_id,
            )
            if result["executed"]:
                _json(result)
        except (FileNotFoundError, ConnectionError, OSError, RuntimeError, ValueError) as exc:
            print(
                f"demo worker {worker_id} waiting: {type(exc).__name__}: {exc}",
                file=sys.stderr,
                flush=True,
            )
        time.sleep(max(1.0, float(idle_sleep)))


def check_running_stack(
    *,
    state_path: str | Path,
    base_url: str,
    token: str | None,
    timeout: float = 90.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + float(timeout)
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            state = read_stack_state(state_path)
            client = AASMRemoteClient(base_url, token, timeout=10.0)
            health = client.health()
            active = client.state(state["active_machine_id"])
            completed = client.state(state["completed_machine_id"])
            history = client._request(
                "GET",
                f"/v1/machines/{state['completed_machine_id']}/history-check",
            )
            worker_ids = {
                row.get("worker_id") for row in active.get("workers", [])
            }
            valid = (
                health.get("runtime_version") == _runtime_version()
                and active.get("snapshot", {}).get("state") == "SELECT"
                and completed.get("snapshot", {}).get("state") == "COMPLETE"
                and "demo-worker-1" in worker_ids
                and bool(history.get("valid"))
            )
            if valid:
                return {
                    "valid": True,
                    "health": health,
                    "stack": state,
                    "active_workers": sorted(worker_ids),
                    "completed_history": history,
                }
            last_error = RuntimeError(
                "stack is reachable but has not satisfied every readiness invariant"
            )
        except Exception as exc:  # readiness loop intentionally captures transport errors
            last_error = exc
        time.sleep(2.0)
    raise RuntimeError(f"AASM demo stack did not become ready: {last_error}")


def _required(value: str | None, name: str) -> str:
    if value:
        return value
    raise SystemExit(f"{name} is required (argument or environment variable)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m aasm.demo_stack",
        description="Operate the canonical AASM v0.27 one-command local stack",
    )
    parser.add_argument(
        "action",
        choices=[
            "bootstrap",
            "fresh",
            "complete",
            "select",
            "status",
            "verify",
            "check",
            "worker",
        ],
    )
    parser.add_argument("--store", default=os.getenv("AASM_STORE"))
    parser.add_argument(
        "--state",
        default=os.getenv("AASM_DEMO_STATE", DEFAULT_STATE_PATH),
    )
    parser.add_argument(
        "--public-url",
        default=os.getenv("AASM_PUBLIC_URL", DEFAULT_PUBLIC_URL),
    )
    parser.add_argument(
        "--url",
        default=os.getenv("AASM_URL", DEFAULT_INTERNAL_URL),
    )
    parser.add_argument("--token", default=os.getenv("AASM_SERVER_TOKEN"))
    parser.add_argument(
        "--worker-id",
        default=os.getenv("AASM_WORKER_ID", "demo-worker-1"),
    )
    parser.add_argument("--selection", default="completed")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--idle-sleep", type=float, default=10.0)
    return parser


def execute(args: argparse.Namespace) -> dict[str, Any] | None:
    state_path = args.state
    if args.action == "bootstrap":
        return bootstrap_stack(
            _required(args.store, "--store / AASM_STORE"),
            state_path=state_path,
            public_url=args.public_url,
        )
    if args.action == "fresh":
        return fresh_stack(
            _required(args.store, "--store / AASM_STORE"),
            state_path=state_path,
            public_url=args.public_url,
        )
    if args.action == "complete":
        return complete_stack(
            _required(args.store, "--store / AASM_STORE"),
            state_path=state_path,
            public_url=args.public_url,
        )
    if args.action == "select":
        return select_stack_machine(args.selection, state_path=state_path)
    if args.action == "status":
        return stack_status(
            _required(args.store, "--store / AASM_STORE"),
            state_path=state_path,
        )
    if args.action == "verify":
        return verify_stack(
            _required(args.store, "--store / AASM_STORE"),
            state_path=state_path,
            selection=args.selection,
        )
    if args.action == "check":
        return check_running_stack(
            state_path=state_path,
            base_url=args.url,
            token=args.token,
            timeout=args.timeout,
        )
    if args.action == "worker":
        worker_forever(
            state_path=state_path,
            base_url=args.url,
            token=args.token,
            worker_id=args.worker_id,
            idle_sleep=args.idle_sleep,
        )
        return None
    raise AssertionError(args.action)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = execute(args)
    if result is not None:
        _json(result)
        if args.action in {"verify", "check"} and not result.get("valid", False):
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
