from __future__ import annotations

from . import cli_v32 as _v32
from .runtime_v32 import AASMEngine
from .reasoning import reasoning_contract, run_reasoning_conformance

# Every inherited stored command must resume the current v0.37 engine.
_v32.AASMEngine = AASMEngine
_v32._v31.AASMEngine = AASMEngine
_v32._v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _json(value):
    _v32._v31._json(value)


def _with_engine(args, callback):
    return _v32._v31._with_engine(args, callback)


def _stored(commands, name: str, help_text: str, func):
    return _v32._v31._stored(commands, name, help_text, func)


def _reasoning_contract(args):
    _json(reasoning_contract())


def _reasoning_conformance(args):
    _json(run_reasoning_conformance())


def _reasoning(args):
    _with_engine(args, lambda engine: _json(engine.reasoning_report()))


def _reasoning_artifact(args):
    _with_engine(args, lambda engine: _json(engine.reasoning_report(args.artifact_id)))


def _reasoning_provenance(args):
    _with_engine(args, lambda engine: _json(engine.reasoning_provenance(args.artifact_id)))


def _reasoning_commit(args):
    _with_engine(
        args,
        lambda engine: _json(
            engine.reasoning_commit(
                args.artifact_id,
                authority_id=args.authority_id,
                authority_class=args.authority_class,
            )
        ),
    )


def build_parser():
    parser = _v32.build_parser()
    commands = _v32._v31._v30._v29._v28._v27._v25._subparsers(parser)

    commands.add_parser(
        "reasoning-contract",
        help="show the v0.37 reasoning artifact and epistemic admission contracts",
    ).set_defaults(func=_reasoning_contract)
    commands.add_parser(
        "reasoning-conformance",
        help="run deterministic reasoning admission and negative-path conformance",
    ).set_defaults(func=_reasoning_conformance)

    _stored(
        commands,
        "reasoning",
        "inspect all durable reasoning artifacts, lifecycle state, and reasoning commits",
        _reasoning,
    )

    command = _stored(
        commands,
        "reasoning-artifact",
        "inspect one durable reasoning artifact and its lifecycle history",
        _reasoning_artifact,
    )
    command.add_argument("artifact_id")

    command = _stored(
        commands,
        "reasoning-provenance",
        "inspect append-only evidence provenance for one reasoning artifact",
        _reasoning_provenance,
    )
    command.add_argument("artifact_id")

    command = _stored(
        commands,
        "reasoning-commit",
        "record an authorized Reasoning Commit over durable reasoning artifacts",
        _reasoning_commit,
    )
    command.add_argument("--artifact-id", action="append", required=True)
    command.add_argument("--authority-id", required=True)
    command.add_argument("--authority-class", choices=["POLICY", "CONTROLLER"], required=True)

    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in (
        "reasoning",
        "reasoning-artifacts",
        "epistemic",
        "reasoning-contract",
        "epistemic-contract",
    ):
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
