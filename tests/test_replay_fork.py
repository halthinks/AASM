from pathlib import Path

from aasm import AASMEngine, MachineState, ProblemSpec, SQLiteStore


def test_replay_at_sequence_returns_historical_state(tmp_path:Path):
    store=SQLiteStore(tmp_path/"runs.db")
    e=AASMEngine(ProblemSpec("history"),store=store)
    e.transition(MachineState.FORMALIZE,"one")
    sequence=e.events[-1].sequence
    historical_hash=e.snapshot.canonical_hash()
    e.transition(MachineState.CLASSIFY,"two")
    old=e.replay(at_sequence=sequence)
    assert old.state == MachineState.FORMALIZE.value
    assert old.canonical_hash() == historical_hash
    store.close()


def test_fork_creates_independent_lineage_without_copying_effects(tmp_path:Path):
    store=SQLiteStore(tmp_path/"runs.db")
    source=AASMEngine(ProblemSpec("fork me"),store=store)
    source.transition(MachineState.FORMALIZE,"normalized")
    fork_sequence=source.events[-1].sequence
    source.transition(MachineState.CLASSIFY,"later")

    forked=source.fork(fork_sequence)
    assert forked.snapshot.machine_id != source.snapshot.machine_id
    assert forked.state == MachineState.FORMALIZE
    lineage=forked.snapshot.metadata["lineage"]
    assert lineage["source_machine_id"] == source.snapshot.machine_id
    assert lineage["source_sequence"] == fork_sequence
    assert forked.list_effects() == []

    forked.transition(MachineState.CLASSIFY,"alternate future")
    assert source.state == MachineState.CLASSIFY
    assert forked.snapshot.machine_id in store.list_unfinished()

    resumed=AASMEngine.resume(forked.snapshot.machine_id,store)
    assert resumed.snapshot.metadata["lineage"]["source_machine_id"] == source.snapshot.machine_id
    store.close()
