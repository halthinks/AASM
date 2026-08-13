from __future__ import annotations

from . import cli_v30 as _v30
from .runtime_v31 import AASMEngine
from .scopes import DecisionScope, ScopeDependency

# Every inherited command resumes the current runtime implementation.
_v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _json(value):
    _v30._emit(value)


def _with_engine(args, callback):
    return _v30._v29._v28._v27._v25._v22._base._with_engine(args, callback)


def _stored(commands, name: str, help_text: str, func):
    command = commands.add_parser(name, help=help_text)
    command.add_argument("machine_id")
    _v30._v29._v28._v27._v25._v22._base._store_args(command)
    command.set_defaults(func=func)
    return command


def _scope_register(args):
    scope = DecisionScope(
        scope_id=args.scope_id,
        name=args.name,
        kind=args.kind,
        parent_scope_id=args.parent_scope_id,
        inheritance=args.inheritance,
        override_policy=args.override_policy,
        metadata={"description": args.description} if args.description else {},
    )
    _with_engine(args, lambda engine: _json(engine.register_scope(scope)))


def _scope_dependency(args):
    dependency = ScopeDependency(
        dependency_id=args.dependency_id,
        upstream_scope_id=args.upstream_scope_id,
        downstream_scope_id=args.downstream_scope_id,
        relation=args.relation,
        invalidation_policy=args.invalidation_policy,
        evidence_ids=list(args.evidence_id or []),
    )
    _with_engine(args, lambda engine: _json(engine.register_scope_dependency(dependency)))


def _scope_report(args):
    _with_engine(args, lambda engine: _json(engine.scope_report()))


def _scope_context(args):
    _with_engine(args, lambda engine: _json(engine.effective_scope_context(args.scope_id)))


def _scope_restart(args):
    _with_engine(
        args,
        lambda engine: _json(
            engine.restart_scope(
                args.scope_id,
                planner_id=args.planner_id,
                reason=args.reason,
            )
        ),
    )


def _scope_migrate(args):
    _with_engine(args, lambda engine: _json(engine.migrate_legacy_scopes()))


def build_parser():
    parser = _v30.build_parser()
    commands = _v30._v29._v28._v27._v25._subparsers(parser)

    command = _stored(
        commands,
        "scope-register",
        "register a hierarchy scope inside the authoritative AASM machine",
        _scope_register,
    )
    command.add_argument("--scope-id", required=True)
    command.add_argument("--name", required=True)
    command.add_argument(
        "--kind",
        choices=["STRATEGY", "ARCHITECTURE", "IMPLEMENTATION", "WORKSTREAM", "CUSTOM"],
        default="CUSTOM",
    )
    command.add_argument("--parent-scope-id", default="root")
    command.add_argument("--inheritance", choices=["INHERIT", "ISOLATED"], default="INHERIT")
    command.add_argument("--override-policy", choices=["EXPLICIT", "DENY"], default="EXPLICIT")
    command.add_argument("--description")

    command = _stored(
        commands,
        "scope-dependency",
        "register a validated cross-scope dependency",
        _scope_dependency,
    )
    command.add_argument("--dependency-id", required=True)
    command.add_argument("--upstream-scope-id", required=True)
    command.add_argument("--downstream-scope-id", required=True)
    command.add_argument(
        "--relation",
        choices=["AUTHORIZES", "CONSTRAINS", "DEPENDS_ON", "REFINES"],
        default="DEPENDS_ON",
    )
    command.add_argument(
        "--invalidation-policy",
        choices=["NONE", "REVALIDATE", "INVALIDATE"],
        default="REVALIDATE",
    )
    command.add_argument("--evidence-id", action="append")

    _stored(
        commands,
        "scope-report",
        "inspect the complete hierarchy, dependencies, effective models, and fairness debt",
        _scope_report,
    )

    command = _stored(
        commands,
        "scope-context",
        "inspect the effective inherited context of one scope",
        _scope_context,
    )
    command.add_argument("scope_id")

    command = _stored(
        commands,
        "scope-restart",
        "restart one scope subtree while preserving parents and siblings",
        _scope_restart,
    )
    command.add_argument("scope_id")
    command.add_argument("--planner-id")
    command.add_argument("--reason", default="operator requested scoped restart")

    _stored(
        commands,
        "scope-migrate",
        "migrate legacy flat calculus records into the canonical root scope",
        _scope_migrate,
    )

    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("scopes", "scope-hierarchy"):
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
