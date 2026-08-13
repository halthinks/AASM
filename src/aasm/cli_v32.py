from __future__ import annotations

from . import cli_v31 as _v31
from .runtime_v32 import AASMEngine

# Rebind inherited resume helpers to the current implementation.
_v31.AASMEngine = AASMEngine
_v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _trace_project(args):
    _v31._with_engine(args, lambda engine: _v31._json(engine.trace_projection()))


def _trace_check(args):
    _v31._with_engine(args, lambda engine: _v31._json(engine.semantic_trace_report()))


def build_parser():
    parser = _v31.build_parser()
    commands = _v31._v30._v29._v28._v27._v25._subparsers(parser)
    _v31._stored(commands, "trace-project", "project authoritative durable events into a lossless formal trace", _trace_project)
    _v31._stored(commands, "trace-check", "run event-linked semantic trace conformance checks", _trace_check)
    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("trace", "trace-semantic"):
        if surface not in choices:
            choices.append(surface)
    inspect._option_string_actions["--surface"].choices = choices
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
