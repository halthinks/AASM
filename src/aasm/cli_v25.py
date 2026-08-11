from __future__ import annotations

import argparse

from . import cli_v22 as _v22
from .decision_backends import BackendBudget
from .runtime_v25 import AASMEngine

_v22._base.AASMEngine = AASMEngine


def _json(value):
    _v22._json(value)


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return _v22._subparsers(parser)


def _stored(commands, name: str, help_text: str, func):
    command = commands.add_parser(name, help=help_text)
    command.add_argument("machine_id")
    _v22._base._store_args(command)
    command.set_defaults(func=func)
    return command


def _backend_report(args):
    _v22._base._with_engine(args, lambda engine: _json(engine.backend_report()))


def _backend_generate(args):
    budget = BackendBudget(
        max_candidates=args.max_candidates,
        max_combinations=args.max_combinations,
        max_cost=args.max_cost,
        max_latency_ms=args.max_latency_ms,
    )
    _v22._base._with_engine(
        args,
        lambda engine: _json(
            engine.generate_candidate_batch(
                args.backend,
                budget=budget,
                continuation=args.continuation,
            )
        ),
    )


def _candidate_records(args):
    _v22._base._with_engine(args, lambda engine: _json({"candidates": engine.candidate_records(status=args.status)}))


def _candidate_select(args):
    _v22._base._with_engine(args, lambda engine: _json(engine.select_candidate(args.candidate_id)))


def _candidate_activate(args):
    _v22._base._with_engine(args, lambda engine: _json(engine.activate_candidate(args.candidate_id)))


def _assurance(args):
    _v22._base._with_engine(args, lambda engine: _json(engine.assurance_report()))


def _history_check(args):
    _v22._base._with_engine(args, lambda engine: _json(engine.check_durable_history(persist=not args.no_persist)))


def _inspect(args):
    if args.surface is None:
        return _v22._base._inspect(args)
    return _v22._base._with_engine(args, lambda engine: _json(engine.inspect_machine(args.surface)))


def build_parser():
    parser = _v22.build_parser()
    commands = _subparsers(parser)

    _stored(commands, "backends", "inspect registered decision backends and candidate history", _backend_report)

    command = _stored(commands, "candidate-generate", "generate a candidate batch through a decision backend", _backend_generate)
    command.add_argument("--backend", default="aasm.finite-domain")
    command.add_argument("--max-candidates", type=int, default=32)
    command.add_argument("--max-combinations", type=int, default=100000)
    command.add_argument("--max-cost", type=float)
    command.add_argument("--max-latency-ms", type=float)
    command.add_argument("--continuation")

    command = _stored(commands, "candidates", "inspect durable candidate lifecycle records", _candidate_records)
    command.add_argument("--status")

    command = _stored(commands, "candidate-select", "select an admissible candidate", _candidate_select)
    command.add_argument("--candidate-id", required=True)

    command = _stored(commands, "candidate-activate", "revalidate and atomically activate a selected candidate", _candidate_activate)
    command.add_argument("--candidate-id", required=True)

    _stored(commands, "assurance", "inspect assurance policy certificates and history checks", _assurance)

    command = _stored(commands, "history-check", "replay and verify durable event history", _history_check)
    command.add_argument("--no-persist", action="store_true")

    command = commands.choices["inspect"]
    command.add_argument(
        "--surface",
        default=None,
        choices=[
            "summary",
            "decisions",
            "obligations",
            "evidence",
            "causal",
            "conflicts",
            "fairness",
            "packages",
            "candidates",
            "assurance",
            "calculus",
            "profile",
        ],
        help="return a domain-neutral machine projection instead of the legacy full run export",
    )
    command.set_defaults(func=_inspect)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
