from __future__ import annotations

from . import cli_v28 as _v28
from .integrations.langgraph import LangGraphAdapter
from .persistence.factory import open_store
from .runtime_v29 import AASMEngine

# All inherited commands resume the current runtime implementation.
_v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _langgraph_binding(args):
    target = getattr(args, "store", None) or getattr(args, "db", None)
    store = open_store(target) if target else None
    try:
        adapter = LangGraphAdapter(
            store=store,
            namespace=args.namespace,
            binding_scope=args.binding_scope,
            engine_class=AASMEngine,
        )
        config = {
            "configurable": {
                "thread_id": args.thread_id,
                **({"run_id": args.run_id} if args.run_id else {}),
            }
        }
        payload = adapter.binding_report(config, goal=args.goal, run_id=args.run_id)
        _v28._v27._v25._json(payload)
        return payload
    finally:
        if store is not None:
            store.close()


def build_parser():
    parser = _v28.build_parser()
    commands = _v28._v27._v25._subparsers(parser)

    command = commands.add_parser(
        "langgraph-binding",
        help="create or inspect a deterministic LangGraph thread/run binding",
    )
    command.add_argument("thread_id")
    command.add_argument("--run-id")
    command.add_argument("--namespace", default="default")
    command.add_argument("--binding-scope", choices=["THREAD", "RUN"], default="THREAD")
    command.add_argument("--goal", default="LangGraph run governed by AASM")
    _v28._v27._v25._v22._base._store_args(command, required=False)
    command.set_defaults(func=_langgraph_binding)

    inspect = commands.choices["inspect"]
    choices = inspect._option_string_actions["--surface"].choices
    inspect._option_string_actions["--surface"].choices = [*choices, "integrations", "langgraph"]
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
