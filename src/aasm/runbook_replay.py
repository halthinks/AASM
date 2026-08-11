from __future__ import annotations

from copy import deepcopy

from .model import ProblemSpec, new_id
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine


def run_replay_fork(*, store=None) -> OperatorRunbookResult:
    """Verify the source history before creating a lineage-bearing fork."""

    store = store_or_memory(store)
    engine = AASMEngine(ProblemSpec("Replay and fork a verified machine"), store=store)
    observation = engine.add_observation(
        "The source machine has a durable observation.",
        source="operator-runbook",
    )
    source_report = engine.check_durable_history(persist=False)
    source_hash = engine.snapshot.canonical_hash()
    replayed = engine.replay()
    source_sequence = engine.events[-1].sequence
    forked = engine.fork(
        source_sequence,
        store=store,
        machine_id=new_id("runbook-fork"),
    )
    lineage = deepcopy(forked.snapshot.metadata.get("lineage") or {})
    source_after = store.load_snapshot(engine.snapshot.machine_id)
    fork_replayed = forked.replay()
    checks = {
        "source_history_valid": source_report["valid"] is True,
        "source_replay_exact": replayed.canonical_hash() == source_hash,
        "source_unchanged": source_after.canonical_hash() == source_hash,
        "fork_has_new_identity": forked.snapshot.machine_id != engine.snapshot.machine_id,
        "lineage_names_source": (
            lineage.get("source_machine_id") == engine.snapshot.machine_id
        ),
        "lineage_names_sequence": int(lineage.get("source_sequence", -1))
        == int(source_sequence),
        "fork_replays": fork_replayed.machine_id == forked.snapshot.machine_id,
    }
    return finish_runbook(
        "replay-fork",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "source_machine_id": engine.snapshot.machine_id,
            "source_sequence": source_sequence,
            "source_snapshot_hash": source_hash,
            "fork_machine_id": forked.snapshot.machine_id,
            "fork_lineage": lineage,
            "observation_id": observation.evidence_id,
        },
        evidence=[
            {
                "kind": "history-check",
                "status": source_report["status"],
                "snapshot_hash": source_report["persisted_snapshot_hash"],
            },
            {"kind": "fork-lineage", **lineage},
        ],
    )
