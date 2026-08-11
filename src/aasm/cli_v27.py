from __future__ import annotations

import argparse

from . import cli_v25 as _v25
from .demo_stack import execute as execute_stack_action


def _serve(args):
    from .server_v27 import serve

    provisioners = artifacts = None
    if args.runtime_config:
        from .supervisor_adapters import load_runtime_registries

        provisioners, artifacts = load_runtime_registries(args.runtime_config)
    return serve(
        args.store,
        args.host,
        args.port,
        args.token,
        provisioners,
        artifacts,
        demo_state_path=args.demo_state,
    )


def _stack(args):
    result = execute_stack_action(args)
    if result is not None:
        _v25._json(result)
        if args.action in {"verify", "check"} and not result.get("valid", False):
            raise SystemExit(2)
    return result


def build_parser():
    parser = _v25.build_parser()
    commands = _v25._subparsers(parser)

    serve_command = commands.choices["serve"]
    serve_command.add_argument(
        "--demo-state",
        help="optional v0.27 local-stack state document exposed to the Control Center",
    )
    serve_command.set_defaults(func=_serve)

    stack = commands.add_parser(
        "stack",
        help="operate the canonical PostgreSQL-backed local reference stack",
    )
    stack.add_argument(
        "action",
        choices=[
            "bootstrap",
            "fresh",
            "complete",
            "select",
            "status",
            "verify",
            "check",
            "worker",
        ],
    )
    stack.add_argument("--store")
    stack.add_argument("--state", default="/var/lib/aasm-demo/stack-state.json")
    stack.add_argument("--public-url", default="http://localhost:8787")
    stack.add_argument("--url", default="http://runtime:8787")
    stack.add_argument("--token")
    stack.add_argument("--worker-id", default="demo-worker-1")
    stack.add_argument("--selection", default="completed")
    stack.add_argument("--timeout", type=float, default=90.0)
    stack.add_argument("--idle-sleep", type=float, default=10.0)
    stack.set_defaults(func=_stack)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
