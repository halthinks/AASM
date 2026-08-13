from __future__ import annotations

import json
from pathlib import Path

from . import cli_v38 as _v38
from .runtime_v39 import AASMEngine
from .typed_capabilities import (
    CapabilityContract,
    CapabilityProvider,
    FormalVerificationPolicy,
    FormalVerificationResult,
    PatternMachine,
    capability_abi_contract,
    formal_verification_contract,
    run_typed_capability_conformance,
    typed_protocol_contract,
)

# Every inherited stored command must resume the current v0.39 engine.
_v38.AASMEngine = AASMEngine
_v38._v37.AASMEngine = AASMEngine
_v38._v37._v32.AASMEngine = AASMEngine
_v38._v37._v32._v31.AASMEngine = AASMEngine
_v38._v37._v32._v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _json(value): _v38._json(value)
def _with_engine(args, callback): return _v38._with_engine(args, callback)
def _stored(commands, name: str, help_text: str, func): return _v38._stored(commands, name, help_text, func)
def _load(path: str): return json.loads(Path(path).read_text(encoding="utf-8"))


def _typed_contract(args): _json(typed_protocol_contract())
def _capability_contract(args): _json(capability_abi_contract())
def _formal_contract(args): _json(formal_verification_contract())
def _conformance(args): _json(run_typed_capability_conformance())
def _patterns(args): _with_engine(args, lambda engine: _json(engine.typed_pattern_report()))
def _transitions(args): _with_engine(args, lambda engine: _json(engine.typed_transition_report()))
def _capabilities(args): _with_engine(args, lambda engine: _json(engine.capability_report()))
def _formal_blueprint(args): _with_engine(args, lambda engine: _json(engine.formal_capability_blueprint()))
def _formal_statements(args): _with_engine(args, lambda engine: _json(engine.formal_statement_report()))
def _formal_report(args): _with_engine(args, lambda engine: _json(engine.formal_verification_report(args.request_id)))


def _pattern_add(args):
    pattern = PatternMachine.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.admit_typed_pattern(
        pattern,
        authority_id=args.authority_id,
        authority_class=args.authority_class,
    )))


def _transition_propose(args):
    payload = _load(args.payload)
    _with_engine(args, lambda engine: _json(engine.propose_typed_transition(
        args.pattern_id,
        args.event,
        payload,
        proposer_id=args.proposer_id,
        evidence_ids=args.evidence_id or [],
    )))


def _transition_authorize(args):
    _with_engine(args, lambda engine: _json(engine.authorize_typed_transition(
        args.decision_id,
        authority_id=args.authority_id,
        authority_class=args.authority_class,
    )))


def _capability_add(args):
    contract = CapabilityContract.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.register_capability_contract(
        contract,
        authority_id=args.authority_id,
        authority_class=args.authority_class,
    )))


def _provider_add(args):
    provider = CapabilityProvider.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.register_capability_provider(
        provider,
        authority_id=args.authority_id,
        authority_class=args.authority_class,
    )))


def _default_contracts(args):
    _with_engine(args, lambda engine: _json(engine.install_default_formal_capability_contracts(
        authority_id=args.authority_id,
        authority_class=args.authority_class,
    )))


def _provider_runtime(args):
    provider = CapabilityProvider.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.register_formal_provider_runtime(
        provider,
        authority_id=args.authority_id,
        authority_class=args.authority_class,
        worker_id=args.worker_id,
        capacity=args.capacity,
        reliability=args.reliability,
        heartbeat_timeout=args.heartbeat_timeout,
    )))


def _formalize(args):
    source = Path(args.source).read_text(encoding="utf-8")
    _with_engine(args, lambda engine: _json(engine.formalize_artifact(
        args.artifact_id,
        logic=args.logic,
        query_mode=args.query_mode,
        canonical_source=source,
        compiler_id=args.compiler_id,
        compiler_version=args.compiler_version,
        conjecture=args.conjecture or "",
    )))


def _formal_request(args):
    policy = FormalVerificationPolicy(
        policy_id=args.policy_id,
        required_independent_results=args.required_independent_results,
        certificate_required=args.certificate_required,
        trusted_kernel_required=args.trusted_kernel_required,
        solver_identity_required=not args.allow_unidentified_solver,
        disagreement_policy=args.disagreement_policy,
    )
    _with_engine(args, lambda engine: _json(engine.request_formal_verification(
        args.formal_statement_id,
        args.capability_id,
        requester_id=args.requester_id,
        linked_artifact_id=args.linked_artifact_id,
        timeout_ms=args.timeout_ms,
        required_providers=args.provider or [],
        policy=policy,
        priority=args.priority,
    )))


def _formal_result(args):
    result = FormalVerificationResult.from_dict(_load(args.input))
    proof = Path(args.proof_object).read_text(encoding="utf-8") if args.proof_object else None
    raw = Path(args.raw_output).read_text(encoding="utf-8") if args.raw_output else None
    _with_engine(args, lambda engine: _json(engine.commit_formal_verification_result(
        result,
        lease_id=args.lease_id,
        proof_object=proof,
        raw_output=raw,
    )))


def _authority(command):
    command.add_argument("--authority-id", required=True)
    command.add_argument("--authority-class", choices=["POLICY", "CONTROLLER"], required=True)


def build_parser():
    parser = _v38.build_parser()
    commands = _v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("typed-protocol-contract", help="show the v0.39 typed event/transition protocol contract").set_defaults(func=_typed_contract)
    commands.add_parser("capability-abi-contract", help="show the v0.39 versioned capability ABI contract").set_defaults(func=_capability_contract)
    commands.add_parser("formal-verification-contract", help="show formalization and theorem-prover epistemic boundaries").set_defaults(func=_formal_contract)
    commands.add_parser("typed-capability-conformance", help="run typed protocol and formal capability conformance").set_defaults(func=_conformance)
    _stored(commands, "typed-patterns", "inspect admitted typed state/event pattern machines", _patterns)
    command = _stored(commands, "typed-pattern-add", "admit a typed pattern through policy authority", _pattern_add); command.add_argument("--input", required=True); _authority(command)
    _stored(commands, "typed-transitions", "inspect typed transition proposals", _transitions)
    command = _stored(commands, "typed-transition-propose", "validate a typed event and propose its legal transition", _transition_propose); command.add_argument("--pattern-id", required=True); command.add_argument("--event", required=True); command.add_argument("--payload", required=True); command.add_argument("--proposer-id", required=True); command.add_argument("--evidence-id", action="append")
    command = _stored(commands, "typed-transition-authorize", "activate a typed transition only after its obligations complete", _transition_authorize); command.add_argument("decision_id"); _authority(command)
    _stored(commands, "capabilities", "inspect admitted capability contracts and providers", _capabilities)
    command = _stored(commands, "capability-add", "admit a versioned capability contract", _capability_add); command.add_argument("--input", required=True); _authority(command)
    command = _stored(commands, "capability-provider-add", "admit a provider bound to an existing resource", _provider_add); command.add_argument("--input", required=True); _authority(command)
    _stored(commands, "formal-blueprint", "show built-in Vampire/Z3/cvc5/Lean capability declarations without admitting them", _formal_blueprint)
    command = _stored(commands, "formal-default-contracts", "admit built-in formal capability contracts", _default_contracts); _authority(command)
    command = _stored(commands, "formal-provider-runtime", "register a formal resource/worker and admit its provider contract", _provider_runtime); command.add_argument("--input", required=True); command.add_argument("--worker-id"); command.add_argument("--capacity", type=float, default=1.0); command.add_argument("--reliability", type=float, default=1.0); command.add_argument("--heartbeat-timeout", type=float, default=60.0); _authority(command)
    _stored(commands, "formal-statements", "inspect provenance-bearing formalizations", _formal_statements)
    command = _stored(commands, "formalize", "record an exact formalization proposal for a reasoning artifact", _formalize); command.add_argument("artifact_id"); command.add_argument("--logic", choices=["tptp", "smtlib2", "lean4", "hol"], required=True); command.add_argument("--query-mode", choices=["VALIDITY", "SATISFIABILITY", "COUNTERMODEL", "EQUIVALENCE", "INVARIANT"], required=True); command.add_argument("--source", required=True); command.add_argument("--conjecture"); command.add_argument("--compiler-id", default="explicit"); command.add_argument("--compiler-version", default="1")
    command = _stored(commands, "formal-request", "create an ordinary obligation and leased verifier tasks for a formal statement", _formal_request); command.add_argument("formal_statement_id"); command.add_argument("--capability-id", required=True); command.add_argument("--requester-id", required=True); command.add_argument("--linked-artifact-id"); command.add_argument("--provider", action="append"); command.add_argument("--timeout-ms", type=int, default=30000); command.add_argument("--priority", type=int, default=0); command.add_argument("--policy-id", default="formal.default"); command.add_argument("--required-independent-results", type=int, default=1); command.add_argument("--certificate-required", action="store_true"); command.add_argument("--trusted-kernel-required", action="store_true"); command.add_argument("--allow-unidentified-solver", action="store_true"); command.add_argument("--disagreement-policy", choices=["INCONCLUSIVE", "FAIL_CLOSED"], default="INCONCLUSIVE")
    command = _stored(commands, "formal-report", "inspect one formal verification request and aggregate", _formal_report); command.add_argument("request_id")
    command = _stored(commands, "formal-result", "commit a leased formal solver result as Evidence", _formal_result); command.add_argument("--input", required=True); command.add_argument("--lease-id", required=True); command.add_argument("--proof-object"); command.add_argument("--raw-output")
    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("typed-protocol", "typed-patterns", "typed-transitions", "capabilities", "capability-abi", "formal-verification", "formal-results", "formal-statements", "formalization", "formal-blueprint"):
        if surface not in choices: choices.append(surface)
    inspect._option_string_actions["--surface"].choices = choices
    return parser


def main(argv=None):
    parser = build_parser(); args = parser.parse_args(argv); return args.func(args)

if __name__ == "__main__": main()
