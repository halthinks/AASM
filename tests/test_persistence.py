from pathlib import Path

from aasm import AASMEngine, MachineState, ProblemSpec
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
