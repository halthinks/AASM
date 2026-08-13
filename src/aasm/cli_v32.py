from __future__ import annotations

import json
from pathlib import Path
from . import cli_v31 as _v31
from .runtime_v32 import AASMEngine
from .trace_conformance import verify_provenance_export, create_selective_provenance_export
from .operator_runbooks import certify_distributed_recovery
from .semantic_result import semantic_problem_contract, semantic_problem_from_document
from .domain_adapters import (
    EnvironmentSnapshot, CompilationCache, ReferenceSemanticCompiler,
    semantic_compiler_contract, compile_semantic_source, run_semantic_compiler_conformance,
)

_v31.AASMEngine = AASMEngine
_v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine

def _trace_project(args): _v31._with_engine(args, lambda engine: _v31._json(engine.trace_projection()))
def _trace_check(args): _v31._with_engine(args, lambda engine: _v31._json(engine.semantic_trace_report()))
def _key(path: str) -> bytes: return Path(path).read_bytes()
def _provenance_export(args): _v31._with_engine(args, lambda engine: _v31._json(engine.provenance_export(args.output, key=_key(args.key_file), signer_id=args.signer_id)))
def _provenance_verify(args): _v31._json(verify_provenance_export(args.source, key=_key(args.key_file), signer_id=args.signer_id))
def _provenance_select(args): _v31._json(create_selective_provenance_export(args.source, args.output, args.include, key=_key(args.key_file), signer_id=args.signer_id or "local"))
def _recovery_certify(args): _v31._json(certify_distributed_recovery())
def _semantic_contract(args): _v31._json(semantic_problem_contract())
def _problem(args): _v31._with_engine(args, lambda engine: _v31._json(engine.semantic_problem_report()))
def _domain(args): _v31._with_engine(args, lambda engine: _v31._json(engine.semantic_domain_report()))
def _problem_admit(args):
    document = json.loads(Path(args.input).read_text(encoding="utf-8")); domain, definition, model, instance = semantic_problem_from_document(document)
    _v31._with_engine(args, lambda engine: _v31._json(engine.admit_semantic_problem(domain, definition, model, instance)))
def _environment(path: str | None) -> EnvironmentSnapshot:
    if not path: return EnvironmentSnapshot()
    value = json.loads(Path(path).read_text(encoding="utf-8")); return EnvironmentSnapshot(**value)
def _write_or_emit(payload, output: str | None):
    if output: Path(output).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    else: _v31._json(payload)
def _compiler_contract(args): _v31._json(semantic_compiler_contract())
def _semantic_compile(args):
    result = compile_semantic_source(args.source, compiler=ReferenceSemanticCompiler(), environment=_environment(args.environment), cache=CompilationCache(), source_name=args.source)
    _write_or_emit(result.to_dict(), args.output)
def _compiler_conformance(args): _v31._json(run_semantic_compiler_conformance())
def _semantic_compile_admit(args):
    environment = _environment(args.environment)
    _v31._with_engine(args, lambda engine: _v31._json(engine.compile_and_admit_semantic(args.source, environment=environment, compiler=ReferenceSemanticCompiler(), cache=CompilationCache(), source_name=args.source)))


def _compile_parser(commands, name: str, help_text: str):
    command = commands.add_parser(name, help=help_text); command.add_argument("source"); command.add_argument("--environment"); command.add_argument("--output"); command.set_defaults(func=_semantic_compile); return command


def build_parser():
    parser = _v31.build_parser(); commands = _v31._v30._v29._v28._v27._v25._subparsers(parser)
    _v31._stored(commands, "trace-project", "project authoritative durable events into a lossless formal trace", _trace_project)
    _v31._stored(commands, "trace-check", "run event-linked semantic trace conformance checks", _trace_check)
    command = _v31._stored(commands, "provenance-export", "export a content-addressed signed run package", _provenance_export)
    command.add_argument("--output", required=True); command.add_argument("--key-file", required=True); command.add_argument("--signer-id", default="local")
    command = commands.add_parser("provenance-verify", help="verify a signed AASM export offline"); command.add_argument("source"); command.add_argument("--key-file", required=True); command.add_argument("--signer-id"); command.set_defaults(func=_provenance_verify)
    command = commands.add_parser("provenance-select", help="create a signed selective-disclosure sub-manifest"); command.add_argument("source"); command.add_argument("--output", required=True); command.add_argument("--include", action="append", required=True); command.add_argument("--key-file", required=True); command.add_argument("--signer-id", default="local"); command.set_defaults(func=_provenance_select)
    commands.add_parser("recovery-certify", help="run deterministic distributed recovery certification").set_defaults(func=_recovery_certify)
    commands.add_parser("semantic-problem-contract", help="show the semantic problem model contract").set_defaults(func=_semantic_contract)
    command = _v31._stored(commands, "problem-admit", "validate and admit a semantic problem document through ordinary AASM evidence", _problem_admit); command.add_argument("--input", required=True)
    _v31._stored(commands, "problem", "inspect the bound semantic ProblemInstance", _problem)
    _v31._stored(commands, "domain", "inspect the bound DomainPackage and ProblemModel", _domain)
    commands.add_parser("semantic-compiler-contract", help="show deterministic semantic compiler contract").set_defaults(func=_compiler_contract)
    _compile_parser(commands, "semantic-compile", "compile semantic source deterministically")
    _compile_parser(commands, "compile", "compatibility alias for semantic-compile")
    _compile_parser(commands, "problem-check", "compile and validate a problem without admission")
    commands.add_parser("semantic-compiler-conformance", help="run semantic compiler conformance fixtures").set_defaults(func=_compiler_conformance)
    command = _v31._stored(commands, "semantic-compile-admit", "compile and admit through the AASM event/reducer boundary", _semantic_compile_admit)
    command.add_argument("--source", required=True); command.add_argument("--environment")
    inspect = commands.choices["inspect"]; choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("trace", "trace-semantic", "provenance", "problem", "semantic-problem", "domain", "semantic-domain", "compiler", "semantic-compiler"):
        if surface not in choices: choices.append(surface)
    inspect._option_string_actions["--surface"].choices = choices
    return parser

def main(argv=None):
    parser = build_parser(); args = parser.parse_args(argv); return args.func(args)

if __name__ == "__main__": main()
