from __future__ import annotations

import json
from pathlib import Path

from aasm.model import ProblemSpec
from aasm.runtime_v55_foundation import AASMEngine
from aasm.semantic_archive import (
    SEMANTIC_ARCHIVE_CONTRACT_ID,
    build_semantic_evolution_archive,
    semantic_archive_contract,
    verify_semantic_evolution_archive,
)
from aasm.semantic_evolution import ProblemDelta, ProblemRevision

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = semantic_archive_contract()
    require(contract["contract_id"] == SEMANTIC_ARCHIVE_CONTRACT_ID, "semantic archive contract drift")
    require(contract["replay"] == "EXISTING_AASM_REDUCER_OVER_ARCHIVED_EVENTS", "archive replay must use existing reducer")
    require(contract["replay_uses_persisted_snapshot"] is False, "archive replay may not shortcut through persisted snapshot")
    require(contract["import_mutation_path"] == "NONE_IN_FOUNDATION", "archive foundation may not create alternate mutation path")
    require(contract["truth_authority"] == "NONE", "archive may not grant truth authority")
    schema = json.loads((ROOT / "schemas" / "semantic-evolution-archive.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == SEMANTIC_ARCHIVE_CONTRACT_ID, "semantic archive schema drift")

    engine = AASMEngine(ProblemSpec("v0.55 archive gate"))
    base = ProblemRevision(
        problem_id="archive-gate-problem",
        problem_fingerprint="archive-problem-r1",
        semantic_projection_fingerprint="archive-semantic-r1",
        revision_id="archive-gate-r1",
    )
    engine.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint="archive-problem-r2",
        target_semantic_projection_fingerprint="archive-semantic-r2",
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint="archive-problem-r2",
        semantic_projection_fingerprint="archive-semantic-r2",
        parent_revision_ids=(base.revision_id,),
        created_from_delta_id=delta.delta_id,
        revision_id="archive-gate-r2",
    )
    engine.commit_problem_revision_transition(delta, target, authority_id="policy", authority_class="POLICY")
    archive = build_semantic_evolution_archive(engine)
    require(archive.to_json() == archive.from_json(archive.to_json()).to_json(), "semantic archive serialization must be byte-stable")
    verification = verify_semantic_evolution_archive(archive)
    require(verification["valid"], f"semantic archive replay verification failed: {verification['errors']}")
    require(verification["persisted_snapshot_used_as_replay_input"] is False, "semantic archive verification used persisted snapshot as replay input")
    require(verification["replayed_canonical_hash"] == engine.snapshot.canonical_hash(), "archived events did not reconstruct exact canonical state")
    print("v0.55 portable semantic evolution archive contracts: PASS")


if __name__ == "__main__":
    main()
