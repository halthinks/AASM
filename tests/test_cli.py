from aasm.cli import build_parser


def test_cli_exposes_durable_commands():
    parser = build_parser()
    for argv, command in [
        (["demo"], "demo"),
        (["runs", "--db", "x.db"], "runs"),
        (["replay", "machine_x", "--db", "x.db"], "replay"),
        (["inspect", "machine_x", "--db", "x.db"], "inspect"),
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
