from pathlib import Path

import pytest

from aasm import AASMEngine, MachineDefinition, MachineState, ProblemSpec
from aasm.persistence import MemoryStore, SQLiteStore


def test_memory_store_replay_matches_live_state():
    store = MemoryStore()
    e = AASMEngine(ProblemSpec("durable", features={"dependency_graph": True}), store=store)
    e.transition(MachineState.FORMALIZE, "normalized")
    e.transition(MachineState.CLASSIFY, "formalized")
    e.classify()
    replayed = e.replay()
    assert replayed.state == e.snapshot.state
    assert replayed.version == e.snapshot.version
    assert replayed.metadata == e.snapshot.metadata
    assert replayed.canonical_hash() == e.snapshot.canonical_hash()


def test_failed_durable_append_does_not_leave_ghost_local_state():
    class RejectOnceStore(MemoryStore):
        def __init__(self):
            super().__init__()
            self.reject_next = False

        def append(self, machine_id, event, snapshot):
            if self.reject_next:
                self.reject_next = False
                raise RuntimeError("simulated durable rejection")
            return super().append(machine_id, event, snapshot)

    store = RejectOnceStore()
    e = AASMEngine(ProblemSpec("reject one durable write"), store=store)
    machine_id = e.snapshot.machine_id
    before = e.snapshot.canonical_hash()
    store.reject_next = True

    with pytest.raises(RuntimeError, match="simulated durable rejection"):
        e.transition(MachineState.FORMALIZE, "must not become a ghost transition")

    assert e.state == MachineState.INGEST
    assert e.snapshot.canonical_hash() == before
    assert e.snapshot.canonical_hash() == store.load_snapshot(machine_id).canonical_hash()
    assert e.replay().canonical_hash() == before


def test_lazy_sqlite_resume_does_not_scan_full_history(tmp_path: Path):
    class CountingSQLiteStore(SQLiteStore):
        def __init__(self, path):
            super().__init__(path)
            self.load_events_calls = []

        def load_events(self, machine_id, after_sequence=0):
            self.load_events_calls.append(after_sequence)
            return super().load_events(machine_id, after_sequence=after_sequence)

    db = tmp_path / "lazy.db"
    seed_store = SQLiteStore(db)
    seed = AASMEngine(ProblemSpec("lazy resume"), store=seed_store)
    seed.transition(MachineState.FORMALIZE, "normalized")
    seed.transition(MachineState.CLASSIFY, "formalized")
    machine_id = seed.snapshot.machine_id
    last_sequence = seed.events[-1].sequence
    seed_store.close()

    store = CountingSQLiteStore(db)
    lazy = AASMEngine.resume(machine_id, store, load_history=False)
    assert store.load_events_calls == []
    assert lazy.state == MachineState.CLASSIFY
    assert lazy._history_loaded is False
    assert lazy._last_sequence == last_sequence

    lazy.transition(MachineState.PLAN, "incremental append")
    assert store.load_events_calls == [last_sequence]
    assert lazy.events[-1].sequence == last_sequence + 1
    assert lazy._history_loaded is False

    exported = lazy.export()
    assert store.load_events_calls[-1] == 0
    assert len(exported["events"]) == last_sequence + 1
    assert lazy._history_loaded is True
    store.close()


def test_lazy_resume_preserves_custom_machine_definition(tmp_path: Path):
    definition = MachineDefinition.from_dict({
        "name": "lazy-custom",
        "start_state": "START",
        "terminal_states": ["DONE"],
        "transitions": {"START": ["WORK"], "WORK": ["DONE"], "DONE": []},
    })
    db = tmp_path / "custom.db"
    store = SQLiteStore(db)
    engine = AASMEngine(ProblemSpec("custom lazy"), store=store, definition=definition)
    engine.transition("WORK", "begin")
    machine_id = engine.snapshot.machine_id
    expected_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(db)
    lazy = AASMEngine.resume(machine_id, reopened, load_history=False)
    assert lazy.definition == definition
    assert lazy.state == "WORK"
    assert lazy.allowed() == ["DONE"]
    assert lazy.snapshot.canonical_hash() == expected_hash
    lazy.transition("DONE", "complete")
    assert lazy.state == "DONE"
    reopened.close()


def test_sqlite_resume_after_engine_is_discarded(tmp_path: Path):
    db = tmp_path / "aasm.db"
    store = SQLiteStore(db)
    first = AASMEngine(ProblemSpec("survive process death"), store=store)
    machine_id = first.snapshot.machine_id
    first.transition(MachineState.FORMALIZE, "normalized")
    first.transition(MachineState.CLASSIFY, "formalized")
    first.classify()
    expected_hash = first.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(db)
    recovered = AASMEngine.resume(machine_id, reopened)
    assert recovered.state == MachineState.CLASSIFY
    assert recovered.snapshot.canonical_hash() == expected_hash
    recovered.transition(MachineState.PLAN, "resume after crash")
    assert reopened.load_snapshot(machine_id).state == MachineState.PLAN.value
    reopened.close()


def test_sqlite_persists_checkpoint_across_restart(tmp_path: Path):
    db = tmp_path / "aasm.db"
    store = SQLiteStore(db)
    e = AASMEngine(ProblemSpec("checkpoint"), store=store)
    e.transition(MachineState.FORMALIZE, "normalized")
    cp = e.checkpoint("known good")
    machine_id = e.snapshot.machine_id
    e.transition(MachineState.CLASSIFY, "formalized")
    e.transition(MachineState.PLAN, "planned")
    e.transition(MachineState.SELECT, "selected")
    e.transition(MachineState.EXECUTE, "executing")
    e.transition(MachineState.OBSERVE, "observed")
    e.transition(MachineState.VERIFY, "verify")
    store.close()

    reopened = SQLiteStore(db)
    recovered = AASMEngine.resume(machine_id, reopened)
    recovered.transition(MachineState.BACKTRACK, "bad branch")
    restored = recovered.backtrack(cp.checkpoint_id)
    assert restored.state == MachineState.FORMALIZE.value
    reopened.close()


def test_recover_unfinished_excludes_terminal_runs(tmp_path: Path):
    store = SQLiteStore(tmp_path / "aasm.db")
    active = AASMEngine(ProblemSpec("active"), store=store)
    active.transition(MachineState.FORMALIZE, "normalized")
    doomed = AASMEngine(ProblemSpec("terminal"), store=store)
    doomed.transition(MachineState.FAIL, "cannot proceed")
    ids = {e.snapshot.machine_id for e in AASMEngine.recover_unfinished(store)}
    assert active.snapshot.machine_id in ids
    assert doomed.snapshot.machine_id not in ids
    store.close()


def test_sqlite_survives_unclean_process_exit(tmp_path: Path):
    import json
    import os
    import subprocess
    import sys

    db = tmp_path / "crash.db"
    marker = tmp_path / "machine.json"
    project_root = Path(__file__).resolve().parents[1]
    code = f'''
import json, os
from aasm import AASMEngine, MachineState, ProblemSpec, SQLiteStore
store=SQLiteStore(r"{db}")
e=AASMEngine(ProblemSpec("unclean crash"), store=store)
e.transition(MachineState.FORMALIZE, "normalized")
e.transition(MachineState.CLASSIFY, "formalized")
e.classify()
open(r"{marker}", "w", encoding="utf-8").write(json.dumps({{"machine_id":e.snapshot.machine_id,"hash":e.snapshot.canonical_hash()}}))
os._exit(73)
'''
    env = dict(os.environ)
    env["PYTHONPATH"] = str(project_root / "src")
    proc = subprocess.run([sys.executable, "-c", code], cwd=project_root, env=env)
    assert proc.returncode == 73
    expected = json.loads(marker.read_text())

    store = SQLiteStore(db)
    recovered = AASMEngine.resume(expected["machine_id"], store)
    assert recovered.snapshot.canonical_hash() == expected["hash"]
    recovered.transition(MachineState.PLAN, "continued after unclean exit")
    assert recovered.state == MachineState.PLAN
    store.close()
