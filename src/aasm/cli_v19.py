from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from .adaptive_routing import ModelOutcomeRecord
from .change_impact import ChangeSignal
from .checkpoint_triggers import CheckpointTriggerPolicy
from .collaboration import CollaborationPolicy
from .codex_telemetry import import_otel_jsonl
from .definitions import MachineDefinition
from .execution_controls import WorkerControlRecord
from .execution_telemetry import TelemetryPolicy
from .fleet_control import FleetControlPolicy
from .governance import GovernanceBudgetPolicy, GovernanceContext
from .mission_control import ForkRequest, MissionControlAction, MissionControlRecord, MissionPauseMode
from .model import MachineState, ProblemSpec
from .model_check import check_machine
from .model_routing import ModelRouteRequest
from .persistence.factory import open_store
from .provisioning import ProvisioningRequest
from .resources import TaskDemand
from .runtime_v19 import AASMEngine
from .team_protocol import BuilderOutput, PlannerDecision, TeamMember, VerifierReport


def _json(value):
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _target(args):
    value = getattr(args, "store", None) or getattr(args, "db", None)
    if not value:
        raise ValueError("a storage target is required")
    return value


def _open(args):
    return open_store(_target(args))


def _store_args(parser, *, required=True):
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--store")
    group.add_argument("--db")


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _with_engine(args, fn):
    store = _open(args)
    try:
        engine = AASMEngine.resume(args.machine_id, store)
        return fn(engine)
    finally:
        store.close()


def _demo(args):
    store = open_store(args.store or args.db) if (args.store or args.db) else None
    try:
        engine = AASMEngine(ProblemSpec("Build verified artifact", features={"dependency_graph": True, "branching_choices": True, "capacity_constraints": True}), store=store)
        engine.transition(MachineState.FORMALIZE, "normalized")
        engine.transition(MachineState.CLASSIFY, "formalized")
        engine.classify()
        engine.transition(MachineState.PLAN, "classified")
        _json(engine.export())
    finally:
        if store:
            store.close()


def _runs(args):
    store = _open(args)
    try:
        _json({"unfinished_runs": store.list_unfinished()})
    finally:
        store.close()


def _replay(args):
    _with_engine(args, lambda e: _json({"machine_id": args.machine_id, "snapshot": asdict(e.replay(at_sequence=args.at))}))


def _fork(args):
    def action(engine):
        forked = engine.fork(args.at)
        _json({"fork_machine_id": forked.snapshot.machine_id, "snapshot": asdict(forked.snapshot)})
    _with_engine(args, action)


def _inspect(args):
    def action(engine):
        payload = engine.export()
        if not args.events:
            payload.pop("events", None)
        _json(payload)
    _with_engine(args, action)


def _simple(name):
    def run(args):
        def action(engine):
            values = {
                "effects": lambda: {"effects": [asdict(row) for row in engine.list_effects()]},
                "plan": lambda: {"graph": engine.snapshot.graph, "frontier": engine.snapshot.frontier, "visited": engine.snapshot.visited, "pruned": engine.snapshot.pruned},
                "memory": lambda: engine.snapshot.memory,
                "resources": lambda: {"resources": engine.list_resources(), "last_schedule": engine.last_schedule()},
                "workers": lambda: {"workers": engine.list_workers(), "quotas": engine.list_quotas(), "leases": engine.list_leases()},
                "models": lambda: {"models": engine.list_model_profiles(), "last_model_route": engine.last_model_route()},
                "economics": engine.economics_summary,
                "governance": engine.governance_report,
                "team": engine.team_report,
                "change-control": lambda: {"paused_tasks": engine.paused_tasks(), "last_impact": engine.last_impact(), "impacts": engine.impact_history()},
                "checkpoint-triggers": lambda: {"policy": asdict(engine.checkpoint_trigger_policy()), "last": engine.last_checkpoint_trigger(), "history": engine.checkpoint_trigger_history()},
                "provisioning": engine.provisioning_report,
                "mission": engine.mission_control_report,
                "effect-queue": engine.effect_queue_report,
                "forks": engine.fork_report,
                "execution-controls": engine.execution_control_report,
                "artifacts": lambda: {"artifacts": engine.external_artifacts(limit=200)},
            }
            _json(values[name]())
        return _with_engine(args, action)
    return run


def _evidence(args):
    def action(engine):
        payload = {"evidence": engine.snapshot.evidence}
        if args.lineage:
            payload["lineage"] = [asdict(row) for row in engine.evidence_lineage(args.lineage)]
        _json(payload)
    _with_engine(args, action)


def _schedule(args):
    _with_engine(args, lambda e: _json(e.schedule([TaskDemand(**row) for row in _load(args.tasks)]).to_dict()))


def _collaboration(args):
    rows = _load(args.tasks) if args.tasks else None
    tasks = None if rows is None else [TaskDemand(**row) for row in rows]
    policy = CollaborationPolicy(**(_load(args.policy) if args.policy else {}))
    _with_engine(args, lambda e: _json(e.analyze_collaboration(tasks, policy)))


def _change_analyze(args):
    _with_engine(args, lambda e: _json(e.analyze_change(ChangeSignal(**_load(args.signal)), pause_affected=not args.no_pause)))


def _change_resolve(args):
    resume = _load(args.resume_nodes) if args.resume_nodes else []
    retire = _load(args.retire_nodes) if args.retire_nodes else []
    _with_engine(args, lambda e: _json(e.resolve_change_impact(args.planner_id, args.impact_id, resume_nodes=resume, retire_nodes=retire, plan_decision_id=args.plan_decision_id)))


def _checkpoint_policy(args):
    _with_engine(args, lambda e: _json(e.configure_checkpoint_triggers(CheckpointTriggerPolicy(**_load(args.policy)))))


def _fleet_control(args):
    def action(engine):
        _json(engine.configure_fleet_control(FleetControlPolicy(**_load(args.policy))) if args.policy else engine.fleet_control_report())
    _with_engine(args, action)


def _fleet_refresh(args):
    policy = CollaborationPolicy(**(_load(args.policy) if args.policy else {}))
    _with_engine(args, lambda e: _json(e.refresh_fleet_control(collaboration_policy=policy)))


def _telemetry(args):
    def action(engine):
        _json(engine.configure_telemetry(TelemetryPolicy(**_load(args.policy))) if args.policy else engine.telemetry_report())
    _with_engine(args, action)


def _telemetry_page(args):
    _with_engine(args, lambda e: _json(e.telemetry_page(cursor=args.cursor, limit=args.limit, task_id=args.task_id, worker_id=args.worker_id, kind=args.kind)))


def _artifact_page(args):
    _with_engine(args, lambda e: _json(e.artifact_page(cursor=args.cursor, limit=args.limit, task_id=args.task_id, worker_id=args.worker_id)))


def _provision_plan(args):
    _with_engine(args, lambda e: _json(e.plan_fleet_provisioning(args.provider, args.resource_id, desired_workers=args.desired_workers)))


def _provision_propose(args):
    _with_engine(args, lambda e: _json(asdict(e.propose_provisioning(ProvisioningRequest(**_load(args.request))))))


def _claim(args):
    _with_engine(args, lambda e: _json(e.claim_task(TaskDemand(**_load(args.task)), args.worker, lease_seconds=args.lease_seconds)))


def _model_route(args):
    _with_engine(args, lambda e: _json(e.route_model(ModelRouteRequest(**_load(args.request))).to_dict()))


def _model_outcome(args):
    _with_engine(args, lambda e: _json(e.record_model_outcome(ModelOutcomeRecord(**_load(args.record)))))


def _model_performance(args):
    _with_engine(args, lambda e: _json({"task_class": args.task_class, "performance": e.model_performance(args.task_class)}))


def _governance_budget(args):
    _with_engine(args, lambda e: _json(e.configure_governance_budget(GovernanceBudgetPolicy(**_load(args.policy)))))


def _governance_decide(args):
    _with_engine(args, lambda e: _json(e.governance_decide(GovernanceContext(**_load(args.context)))))


def _governance_complete(args):
    evidence = _load(args.evidence) if args.evidence else []
    _with_engine(args, lambda e: _json(e.complete_governance_review(args.decision_id, evidence=evidence)))


def _team_init(args):
    _with_engine(args, lambda e: _json(e.initialize_team([TeamMember(**row) for row in _load(args.members)])))


def _builder_output(args):
    _with_engine(args, lambda e: _json(e.submit_builder_output(BuilderOutput(**_load(args.record)))))


def _verifier_report(args):
    _with_engine(args, lambda e: _json(e.submit_verifier_report(VerifierReport(**_load(args.record)))))


def _planner_decision(args):
    _with_engine(args, lambda e: _json(e.planner_decide(PlannerDecision(**_load(args.record)))))


def _codex_telemetry(args):
    _with_engine(args, lambda e: _json(e.import_codex_telemetry(import_otel_jsonl(args.jsonl))))


def _mission_pause(args):
    record = MissionControlRecord(MissionControlAction.PAUSE, args.actor, args.reason, args.mode)
    _with_engine(args, lambda e: _json(e.pause_mission(record)))


def _mission_resume(args):
    record = MissionControlRecord(MissionControlAction.RESUME, args.actor, args.reason)
    _with_engine(args, lambda e: _json(e.resume_mission(record)))


def _effect_authorize(args):
    _with_engine(args, lambda e: _json(e.authorize_pending_effect(args.effect_id, args.actor, args.reason)))


def _fork_propose(args):
    def action(engine):
        request = ForkRequest(
            source_sequence=engine.current_sequence() if args.at is None else args.at,
            actor=args.actor,
            reason=args.reason,
            target_machine_id=args.target_machine_id,
        ) if args.target_machine_id else ForkRequest(
            source_sequence=engine.current_sequence() if args.at is None else args.at,
            actor=args.actor,
            reason=args.reason,
        )
        _json(asdict(engine.propose_fork(request)))
    _with_engine(args, action)


def _fork_execute(args):
    _with_engine(args, lambda e: _json(asdict(e.execute_fork(args.effect_id))))


def _worker_control(args):
    record = WorkerControlRecord(args.worker_id, args.action, args.actor, args.reason)
    _with_engine(args, lambda e: _json(e.control_worker(record)))


def _serve(args):
    from .server_v19 import serve
    provisioners = artifacts = None
    if args.runtime_config:
        from .supervisor_adapters import load_runtime_registries
        provisioners, artifacts = load_runtime_registries(args.runtime_config)
    serve(args.store, args.host, args.port, args.token, provisioners, artifacts)


def _worker(args):
    from .codex_executor import CodexCLIExecutor
    from .executor_orchestration import ExecutorBinding, ExecutorRegistry, OrchestratedRemoteWorker
    from .openai_executor import OpenAIResponsesExecutor
    from .remote_v19 import AASMRemoteClient
    from .workers import WorkerRecord

    adapter = CodexCLIExecutor(cwd=args.cwd) if args.executor == "codex" else OpenAIResponsesExecutor()
    registry = ExecutorRegistry()
    registry.register(ExecutorBinding(args.executor_id, adapter, [args.provider], args.capability, priority=args.priority, metadata={"kind": args.executor}))
    worker = WorkerRecord(args.worker_id, args.resource_id, metadata={"executors": registry.describe()})
    runtime = OrchestratedRemoteWorker(AASMRemoteClient(args.url, args.token, timeout=args.http_timeout), args.machine_id, worker, registry, lease_seconds=args.lease_seconds, heartbeat_interval=args.heartbeat_interval, idle_sleep=args.idle_sleep)
    if args.once:
        _json({"executed": runtime.run_once()})
    else:
        runtime.run_forever()


def _verify_machine(args):
    report = check_machine(MachineDefinition.load(args.path))
    _json(report.to_dict())
    if not report.valid:
        raise SystemExit(2)


def build_parser():
    parser = argparse.ArgumentParser(prog="aasm")
    commands = parser.add_subparsers(dest="command", required=True)

    def stored(name, help_text, func, *, store=True):
        command = commands.add_parser(name, help=help_text)
        if store:
            command.add_argument("machine_id")
            _store_args(command)
        command.set_defaults(func=func)
        return command

    command = commands.add_parser("demo", help="run demo")
    _store_args(command, required=False)
    command.set_defaults(func=_demo)
    command = commands.add_parser("runs", help="list unfinished runs")
    _store_args(command)
    command.set_defaults(func=_runs)

    command = stored("replay", "replay a run", _replay); command.add_argument("--at", type=int)
    command = stored("fork", "low-level immediate fork for embedded/local authority", _fork); command.add_argument("--at", type=int, required=True)
    command = stored("inspect", "inspect run", _inspect); command.add_argument("--events", action="store_true")
    for name in ["effects", "plan", "memory", "resources", "workers", "models", "economics", "governance", "team", "change-control", "checkpoint-triggers", "provisioning", "mission", "effect-queue", "forks", "execution-controls", "artifacts"]:
        stored(name, name, _simple(name))

    command = stored("evidence", "inspect evidence", _evidence); command.add_argument("--lineage")
    command = stored("schedule", "compute resource schedule", _schedule); command.add_argument("--tasks", required=True)
    command = stored("collaboration", "analyze useful worker fan-out", _collaboration); command.add_argument("--tasks"); command.add_argument("--policy")
    command = stored("change-analyze", "selectively pause impacted work", _change_analyze); command.add_argument("--signal", required=True); command.add_argument("--no-pause", action="store_true")
    command = stored("change-resolve", "resolve change checkpoint", _change_resolve); command.add_argument("--impact-id", required=True); command.add_argument("--planner-id", required=True); command.add_argument("--resume-nodes"); command.add_argument("--retire-nodes"); command.add_argument("--plan-decision-id")
    command = stored("checkpoint-trigger-policy", "configure verifier checkpoint triggers", _checkpoint_policy); command.add_argument("--policy", required=True)
    command = stored("fleet-control", "inspect/configure fleet admission", _fleet_control); command.add_argument("--policy")
    command = stored("fleet-refresh", "recompute fleet admission", _fleet_refresh); command.add_argument("--policy")
    command = stored("telemetry", "inspect/configure telemetry", _telemetry); command.add_argument("--policy")
    command = stored("telemetry-page", "page execution telemetry", _telemetry_page); command.add_argument("--cursor"); command.add_argument("--limit", type=int, default=100); command.add_argument("--task-id"); command.add_argument("--worker-id"); command.add_argument("--kind")
    command = stored("artifact-page", "page external artifact references", _artifact_page); command.add_argument("--cursor"); command.add_argument("--limit", type=int, default=100); command.add_argument("--task-id"); command.add_argument("--worker-id")
    command = stored("provision-plan", "plan physical worker delta", _provision_plan); command.add_argument("--provider", required=True); command.add_argument("--resource-id", required=True); command.add_argument("--desired-workers", type=int)
    command = stored("provision-propose", "propose authority-gated provisioning effect", _provision_propose); command.add_argument("--request", required=True)
    command = stored("claim", "claim one task", _claim); command.add_argument("--worker", required=True); command.add_argument("--task", required=True); command.add_argument("--lease-seconds", type=float, default=60)
    command = stored("model-route", "route a model", _model_route); command.add_argument("--request", required=True)
    command = stored("model-outcome", "record evaluated model outcome", _model_outcome); command.add_argument("--record", required=True)
    command = stored("model-performance", "inspect empirical model performance", _model_performance); command.add_argument("--task-class")
    command = stored("governance-budget", "configure governance budget", _governance_budget); command.add_argument("--policy", required=True)
    command = stored("governance-decide", "evaluate semantic review", _governance_decide); command.add_argument("--context", required=True)
    command = stored("governance-complete", "complete semantic review", _governance_complete); command.add_argument("--decision-id", required=True); command.add_argument("--evidence")
    command = stored("team-init", "initialize Planner/Builder/Verifier team", _team_init); command.add_argument("--members", required=True)
    command = stored("builder-output", "record Builder output", _builder_output); command.add_argument("--record", required=True)
    command = stored("verifier-report", "record Verifier report", _verifier_report); command.add_argument("--record", required=True)
    command = stored("planner-decision", "commit Planner directive", _planner_decision); command.add_argument("--record", required=True)
    command = stored("codex-telemetry", "import Codex telemetry", _codex_telemetry); command.add_argument("--jsonl", required=True)
    command = stored("mission-pause", "pause mission admission", _mission_pause); command.add_argument("--actor", required=True); command.add_argument("--reason", required=True); command.add_argument("--mode", choices=[MissionPauseMode.QUIESCE, MissionPauseMode.SUSPEND], default=MissionPauseMode.QUIESCE)
    command = stored("mission-resume", "resume mission admission", _mission_resume); command.add_argument("--actor", required=True); command.add_argument("--reason", required=True)
    command = stored("effect-authorize", "approve a pending effect without executing it", _effect_authorize); command.add_argument("--effect-id", required=True); command.add_argument("--actor", required=True); command.add_argument("--reason", required=True)
    command = stored("fork-propose", "propose controlled fork effect", _fork_propose); command.add_argument("--at", type=int); command.add_argument("--actor", required=True); command.add_argument("--reason", required=True); command.add_argument("--target-machine-id")
    command = stored("fork-execute", "execute authorized controlled fork", _fork_execute); command.add_argument("--effect-id", required=True)
    command = stored("worker-control", "drain/resume/offline worker", _worker_control); command.add_argument("--worker-id", required=True); command.add_argument("--action", choices=["DRAIN", "RESUME", "OFFLINE"], required=True); command.add_argument("--actor", required=True); command.add_argument("--reason", required=True)

    command = commands.add_parser("serve", help="serve control plane")
    command.add_argument("--store", required=True); command.add_argument("--host", default="127.0.0.1"); command.add_argument("--port", type=int, default=8787); command.add_argument("--token"); command.add_argument("--runtime-config"); command.set_defaults(func=_serve)
    command = commands.add_parser("worker", help="run executor worker")
    command.add_argument("--url", required=True); command.add_argument("--machine-id", required=True); command.add_argument("--worker-id", required=True); command.add_argument("--resource-id", required=True); command.add_argument("--executor", choices=["codex", "responses"], required=True); command.add_argument("--executor-id", default="default"); command.add_argument("--provider", default="openai"); command.add_argument("--capability", action="append", default=[]); command.add_argument("--priority", type=int, default=0); command.add_argument("--cwd"); command.add_argument("--token"); command.add_argument("--lease-seconds", type=float, default=120); command.add_argument("--heartbeat-interval", type=float, default=20); command.add_argument("--idle-sleep", type=float, default=2); command.add_argument("--http-timeout", type=float, default=30); command.add_argument("--once", action="store_true"); command.set_defaults(func=_worker)
    command = commands.add_parser("verify-machine", help="verify declarative machine")
    command.add_argument("path"); command.set_defaults(func=_verify_machine)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)
