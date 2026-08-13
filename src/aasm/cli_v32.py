from __future__ import annotations

from pathlib import Path
from . import cli_v31 as _v31
from .runtime_v32 import AASMEngine
from .trace_conformance import verify_provenance_export, create_selective_provenance_export
from .operator_runbooks import certify_distributed_recovery

_v31.AASMEngine = AASMEngine
_v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine

def _trace_project(args): _v31._with_engine(args, lambda engine: _v31._json(engine.trace_projection()))
def _trace_check(args): _v31._with_engine(args, lambda engine: _v31._json(engine.semantic_trace_report()))
def _key(path: str) -> bytes: return Path(path).read_bytes()
def _provenance_export(args): _v31._with_engine(args, lambda engine: _v31._json(engine.provenance_export(args.output, key=_key(args.key_file), signer_id=args.signer_id)))
def _provenance_verify(args): _v31._json(verify_provenance_export(args.source, key=_key(args.key_file), signer_id=args.signer_id))
def _provenance_select(args): _v31._json(create_selective_provenance_export(args.source, args.output, args.include, key=_key(args.key_file), signer_id=args.signer_id or "local"))
def _recovery_certify(args): _v31._json(certify_distributed_recovery())

def build_parser():
    parser = _v31.build_parser(); commands = _v31._v30._v29._v28._v27._v25._subparsers(parser)
    _v31._stored(commands, "trace-project", "project authoritative durable events into a lossless formal trace", _trace_project)
    _v31._stored(commands, "trace-check", "run event-linked semantic trace conformance checks", _trace_check)
    command = _v31._stored(commands, "provenance-export", "export a content-addressed signed run package", _provenance_export)
    command.add_argument("--output", required=True); command.add_argument("--key-file", required=True); command.add_argument("--signer-id", default="local")
    command = commands.add_parser("provenance-verify", help="verify a signed AASM export offline")
    command.add_argument("source"); command.add_argument("--key-file", required=True); command.add_argument("--signer-id"); command.set_defaults(func=_provenance_verify)
    command = commands.add_parser("provenance-select", help="create a signed selective-disclosure sub-manifest")
    command.add_argument("source"); command.add_argument("--output", required=True); command.add_argument("--include", action="append", required=True); command.add_argument("--key-file", required=True); command.add_argument("--signer-id", default="local"); command.set_defaults(func=_provenance_select)
    command = commands.add_parser("recovery-certify", help="run deterministic distributed recovery certification")
    command.set_defaults(func=_recovery_certify)
    inspect = commands.choices["inspect"]; choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("trace", "trace-semantic", "provenance"):
        if surface not in choices: choices.append(surface)
    inspect._option_string_actions["--surface"].choices = choices
    return parser

def main(argv=None):
    parser = build_parser(); args = parser.parse_args(argv); return args.func(args)

if __name__ == "__main__": main()
