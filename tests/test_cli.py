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
