from aasm.cli import build_parser


def test_cli_exposes_durable_commands():
    parser = build_parser()
    cases = [
        (["demo"], "demo"),
        (["runs", "--db", "x.db"], "runs"),
        (["runs", "--store", "postgresql://example/aasm"], "runs"),
        (["replay", "machine_x", "--db", "x.db"], "replay"),
        (["replay", "machine_x", "--db", "x.db", "--at", "3"], "replay"),
        (["fork", "machine_x", "--db", "x.db", "--at", "3"], "fork"),
        (["verify-machine", "machine.json"], "verify-machine"),
        (["inspect", "machine_x", "--db", "x.db"], "inspect"),
        (["plan", "machine_x", "--db", "x.db"], "plan"),
        (["memory", "machine_x", "--db", "x.db"], "memory"),
        (["evidence", "machine_x", "--db", "x.db"], "evidence"),
        (["resources", "machine_x", "--db", "x.db"], "resources"),
        (["schedule", "machine_x", "--db", "x.db", "--tasks", "tasks.json"], "schedule"),
        (["collaboration", "machine_x", "--store", "x.db"], "collaboration"),
        (["change-control", "machine_x", "--store", "x.db"], "change-control"),
        (["change-analyze", "machine_x", "--store", "x.db", "--signal", "signal.json"], "change-analyze"),
        (["change-resolve", "machine_x", "--store", "x.db", "--impact-id", "impact_1", "--planner-id", "planner"], "change-resolve"),
        (["checkpoint-triggers", "machine_x", "--store", "x.db"], "checkpoint-triggers"),
        (["checkpoint-trigger-policy", "machine_x", "--store", "x.db", "--policy", "checkpoint.json"], "checkpoint-trigger-policy"),
        (["fleet-control", "machine_x", "--store", "x.db"], "fleet-control"),
        (["fleet-refresh", "machine_x", "--store", "x.db"], "fleet-refresh"),
        (["telemetry", "machine_x", "--store", "x.db"], "telemetry"),
        (["telemetry-page", "machine_x", "--store", "x.db", "--limit", "25"], "telemetry-page"),
        (["provisioning", "machine_x", "--store", "x.db"], "provisioning"),
        (["provision-plan", "machine_x", "--store", "x.db", "--provider", "fake", "--resource-id", "pool"], "provision-plan"),
        (["provision-propose", "machine_x", "--store", "x.db", "--request", "request.json"], "provision-propose"),
        (["mission", "machine_x", "--store", "x.db"], "mission"),
        (["mission-pause", "machine_x", "--store", "x.db", "--actor", "operator", "--reason", "hold"], "mission-pause"),
        (["mission-resume", "machine_x", "--store", "x.db", "--actor", "operator", "--reason", "continue"], "mission-resume"),
        (["effect-queue", "machine_x", "--store", "x.db"], "effect-queue"),
        (["effect-authorize", "machine_x", "--store", "x.db", "--effect-id", "e1", "--actor", "operator", "--reason", "approved"], "effect-authorize"),
        (["forks", "machine_x", "--store", "x.db"], "forks"),
        (["fork-propose", "machine_x", "--store", "x.db", "--actor", "operator", "--reason", "alternate"], "fork-propose"),
        (["fork-execute", "machine_x", "--store", "x.db", "--effect-id", "e1"], "fork-execute"),
        (["execution-controls", "machine_x", "--store", "x.db"], "execution-controls"),
        (["worker-control", "machine_x", "--store", "x.db", "--worker-id", "w1", "--action", "DRAIN", "--actor", "operator", "--reason", "maintenance"], "worker-control"),
        (["artifacts", "machine_x", "--store", "x.db"], "artifacts"),
        (["artifact-page", "machine_x", "--store", "x.db", "--limit", "25"], "artifact-page"),
        (["economics", "machine_x", "--store", "x.db"], "economics"),
        (["governance", "machine_x", "--store", "x.db"], "governance"),
        (["governance-budget", "machine_x", "--store", "x.db", "--policy", "budget.json"], "governance-budget"),
        (["governance-decide", "machine_x", "--store", "x.db", "--context", "context.json"], "governance-decide"),
        (["governance-complete", "machine_x", "--store", "x.db", "--decision-id", "gov_1"], "governance-complete"),
        (["codex-telemetry", "machine_x", "--store", "x.db", "--jsonl", "otel.jsonl"], "codex-telemetry"),
        (["model-outcome", "machine_x", "--store", "x.db", "--record", "outcome.json"], "model-outcome"),
        (["model-performance", "machine_x", "--store", "x.db", "--task-class", "backend"], "model-performance"),
        (["team", "machine_x", "--store", "x.db"], "team"),
        (["team-init", "machine_x", "--store", "x.db", "--members", "members.json"], "team-init"),
        (["builder-output", "machine_x", "--store", "x.db", "--record", "builder.json"], "builder-output"),
        (["verifier-report", "machine_x", "--store", "x.db", "--record", "verifier.json"], "verifier-report"),
        (["planner-decision", "machine_x", "--store", "x.db", "--record", "decision.json"], "planner-decision"),
        (["serve", "--store", "x.db", "--runtime-config", "runtime.json"], "serve"),
    ]
    for argv, command in cases:
        assert parser.parse_args(argv).command == command


def test_cli_effects_lists_persisted_effect(tmp_path, capsys):
    from aasm import AASMEngine, EffectSpec, ProblemSpec, SQLiteStore
    from aasm.cli import main
    import sys

    database = tmp_path / "cli-effects.db"
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("cli effects"), store=store)
    record = engine.propose_effect(EffectSpec("tool", idempotency_key="cli-key"))
    engine.authorize_effect(record.spec.effect_id)
    engine.execute_effect(record.spec.effect_id, lambda spec, key: {"ok": True})
    machine_id = engine.snapshot.machine_id
    store.close()
    previous = sys.argv
    try:
        sys.argv = ["aasm", "effects", machine_id, "--db", str(database)]
        main()
    finally:
        sys.argv = previous
    output = capsys.readouterr().out
    assert '"status": "SUCCEEDED"' in output
    assert '"idempotency_key": "cli-key"' in output


def test_cli_verify_machine_reports_valid(tmp_path, capsys):
    from aasm.cli import main
    import json
    import sys

    path = tmp_path / "machine.json"
    path.write_text(json.dumps({"name": "ok", "start_state": "A", "terminal_states": ["DONE"], "transitions": {"A": ["DONE"], "DONE": []}}))
    previous = sys.argv
    try:
        sys.argv = ["aasm", "verify-machine", str(path)]
        main()
    finally:
        sys.argv = previous
    assert '"valid": true' in capsys.readouterr().out
