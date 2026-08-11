from __future__ import annotations

from . import cli_v27 as _v27
from .cli_v19 import _store_args
from .operator_runbooks import (
    RUNBOOK_DEFINITIONS,
    execute_operator_runbook,
    list_operator_runbooks,
)
from .persistence.factory import open_store


def _runbook(args):
    if args.runbook_id == "list":
        payload = {"runbooks": list_operator_runbooks()}
        _v27._v25._json(payload)
        return payload
    target = getattr(args, "store", None) or getattr(args, "db", None)
    store = open_store(target) if target else None
    try:
        result = execute_operator_runbook(args.runbook_id, store=store)
        payload = result.to_dict()
        _v27._v25._json(payload)
        if not result.valid:
            raise SystemExit(2)
        return result
    finally:
        if store is not None:
            store.close()


def build_parser():
    parser = _v27.build_parser()
    commands = _v27._v25._subparsers(parser)

    command = commands.add_parser(
        "runbook",
        help="list or execute a tested operator recovery drill",
    )
    command.add_argument(
        "runbook_id",
        choices=["list", *sorted(RUNBOOK_DEFINITIONS)],
        help="runbook identifier or 'list'",
    )
    _store_args(command, required=False)
    command.set_defaults(func=_runbook)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
