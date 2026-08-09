from __future__ import annotations

import argparse

from .cli_v19 import _json, _store_args, _with_engine, build_parser as build_v19_parser


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("AASM CLI parser has no subparser action")


def _calculus(args):
    _with_engine(args, lambda engine: _json(engine.calculus_report()))


def _calculus_fairness(args):
    _with_engine(args, lambda engine: _json(engine.audit_calculus_fairness()))


def build_parser():
    parser = build_v19_parser()
    commands = _subparsers(parser)

    command = commands.add_parser("calculus", help="inspect formal-calculus state")
    command.add_argument("machine_id")
    _store_args(command)
    command.set_defaults(func=_calculus)

    command = commands.add_parser("calculus-fairness", help="audit persistent-obligation fairness")
    command.add_argument("machine_id")
    _store_args(command)
    command.set_defaults(func=_calculus_fairness)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
