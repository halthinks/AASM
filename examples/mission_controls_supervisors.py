"""AASM v0.19 mission controls, controlled fork, and local fleet config."""

from aasm import (
    AASMEngine,
    ForkRequest,
    MissionControlAction,
    MissionControlRecord,
    MissionPauseMode,
    ProblemSpec,
)


engine = AASMEngine(ProblemSpec("Operate a controlled multi-agent mission"))

engine.pause_mission(MissionControlRecord(
    MissionControlAction.PAUSE,
    "operator",
    "inspect an unexpected result before admitting more work",
    MissionPauseMode.QUIESCE,
))
print(engine.mission_control_report())

engine.resume_mission(MissionControlRecord(
    MissionControlAction.RESUME,
    "operator",
    "review complete",
))

fork = engine.propose_fork(ForkRequest(
    engine.current_sequence(),
    "operator",
    "evaluate an alternate plan without disturbing the canonical run",
))
print("pending fork effect:", fork.spec.effect_id)
print(engine.effect_queue_report())

# Production code deliberately performs these as separate operator actions:
# engine.authorize_pending_effect(fork.spec.effect_id, "operator", "approved")
# engine.execute_fork(fork.spec.effect_id)
