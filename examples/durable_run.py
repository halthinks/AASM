"""Minimal durable AASM run with replay/resume."""
from pathlib import Path

from aasm import AASMEngine, MachineState, ProblemSpec, SQLiteStore

DB = Path("aasm-demo.db")
store = SQLiteStore(DB)
engine = AASMEngine(ProblemSpec("Produce a durable verified artifact"), store=store)
engine.transition(MachineState.FORMALIZE, "goal normalized")
engine.transition(MachineState.CLASSIFY, "problem formalized")
engine.classify()
machine_id = engine.snapshot.machine_id
print("created", machine_id, engine.state.value)
store.close()

# Simulate a new process opening the same database.
store = SQLiteStore(DB)
recovered = AASMEngine.resume(machine_id, store)
print("recovered", recovered.snapshot.machine_id, recovered.state.value)
print("replay hash", recovered.replay().canonical_hash())
store.close()
