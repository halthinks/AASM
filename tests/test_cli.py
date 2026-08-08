from aasm.cli import build_parser


def test_cli_exposes_durable_commands():
    parser = build_parser()
    for argv, command in [
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
        (["economics", "machine_x", "--store", "x.db"], "economics"),
        (["codex-telemetry", "machine_x", "--store", "x.db", "--jsonl", "otel.jsonl"], "codex-telemetry"),
        (["model-outcome", "machine_x", "--store", "x.db", "--record", "outcome.json"], "model-outcome"),
        (["model-performance", "machine_x", "--store", "x.db", "--task-class", "backend"], "model-performance"),
    ]:
        assert parser.parse_args(argv).command == command


def test_cli_effects_lists_persisted_effect(tmp_path, capsys):
    from aasm import AASMEngine, EffectSpec, ProblemSpec, SQLiteStore
    from aasm.cli import main
    import sys
    db=tmp_path/"cli-effects.db"
    store=SQLiteStore(db)
    e=AASMEngine(ProblemSpec("cli effects"),store=store)
    r=e.propose_effect(EffectSpec("tool",idempotency_key="cli-key"))
    e.authorize_effect(r.spec.effect_id)
    e.execute_effect(r.spec.effect_id,lambda spec,key:{"ok":True})
    mid=e.snapshot.machine_id
    store.close()
    old=sys.argv
    try:
        sys.argv=["aasm","effects",mid,"--db",str(db)]
        main()
    finally:
        sys.argv=old
    out=capsys.readouterr().out
    assert '"status": "SUCCEEDED"' in out
    assert '"idempotency_key": "cli-key"' in out


def test_cli_verify_machine_reports_valid(tmp_path, capsys):
    from aasm.cli import main
    import json, sys
    path=tmp_path/"machine.json"
    path.write_text(json.dumps({"name":"ok","start_state":"A","terminal_states":["DONE"],"transitions":{"A":["DONE"],"DONE":[]}}))
    old=sys.argv
    try:
        sys.argv=["aasm","verify-machine",str(path)]
        main()
    finally:
        sys.argv=old
    out=capsys.readouterr().out
    assert '"valid": true' in out
