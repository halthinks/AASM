from __future__ import annotations

import json
from pathlib import Path

from . import cli_v37 as _v37
from .runtime_v32 import AASMEngine
from .semantic_dependencies import CausalDecisionRecord, ReactiveObligationRule, SemanticDependency, semantic_dependency_contract, run_semantic_dependency_conformance

_v37.AASMEngine = AASMEngine
_v37._v32.AASMEngine = AASMEngine
_v37._v32._v31.AASMEngine = AASMEngine
_v37._v32._v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _json(value): _v37._json(value)
def _with_engine(args, callback): return _v37._with_engine(args, callback)
def _stored(commands, name: str, help_text: str, func): return _v37._stored(commands, name, help_text, func)
def _load(path: str): return json.loads(Path(path).read_text(encoding="utf-8"))
def _dependency_contract(args): _json(semantic_dependency_contract())
def _dependency_conformance(args): _json(run_semantic_dependency_conformance())
def _dependency_graph(args): _with_engine(args, lambda engine: _json(engine.semantic_dependency_graph()))
def _dependency_impact(args): _with_engine(args, lambda engine: _json(engine.semantic_dependency_impact(args.node_type, args.node_id)))
def _dependency_lineage(args): _with_engine(args, lambda engine: _json(engine.semantic_dependency_lineage(args.node_type, args.node_id)))

def _dependency_add(args):
    dependency = SemanticDependency.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.register_semantic_dependency(dependency, authority_id=args.authority_id, authority_class=args.authority_class)))

def _causal_decision_add(args):
    record = CausalDecisionRecord(**_load(args.input))
    def action(engine):
        registered = engine.register_causal_decision(record)
        if args.activate: registered["activation"] = engine.activate_decision(record.decision_id)
        _json(registered)
    _with_engine(args, action)

def _reactive_rule_add(args):
    rule = ReactiveObligationRule.from_dict(_load(args.input))
    _with_engine(args, lambda engine: _json(engine.register_reactive_obligation_rule(rule, authority_id=args.authority_id, authority_class=args.authority_class)))

def _reactive_derive(args): _with_engine(args, lambda engine: _json(engine.derive_reactive_obligations(from_sequence=args.from_sequence)))
def _reactive_obligations(args): _with_engine(args, lambda engine: _json(engine.reactive_obligation_report()))

def _truth_maintain(args):
    _with_engine(args, lambda engine: _json(engine.apply_truth_change(args.node_type, args.node_id, reason=args.reason, authority_id=args.authority_id, authority_class=args.authority_class, evidence_ids=args.evidence_id or [])))

def _truth_resume(args): _with_engine(args, lambda engine: _json(engine.resume_truth_maintenance(args.plan_id)))
def _truth_report(args): _with_engine(args, lambda engine: _json(engine.truth_maintenance_report()))
def _memory_signals(args): _with_engine(args, lambda engine: _json(engine.semantic_memory_projection_signals()))

def _node_args(command):
    command.add_argument("--node-type", required=True)
    command.add_argument("--node-id", required=True)


def build_parser():
    parser = _v37.build_parser()
    commands = _v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("semantic-dependency-contract", help="show the v0.38 semantic dependency and truth-maintenance contract").set_defaults(func=_dependency_contract)
    commands.add_parser("semantic-dependency-conformance", help="run semantic dependency, truth-maintenance, and reactive-obligation conformance").set_defaults(func=_dependency_conformance)
    _stored(commands, "dependency-graph", "inspect the deterministic semantic dependency graph", _dependency_graph)
    command = _stored(commands, "dependency-impact", "show affected descendants if one semantic node changes", _dependency_impact); _node_args(command)
    command = _stored(commands, "dependency-lineage", "show backward semantic proof and dependency lineage", _dependency_lineage); _node_args(command)
    command = _stored(commands, "dependency-add", "admit an explicit semantic dependency through ordinary AASM Evidence", _dependency_add); command.add_argument("--input", required=True); command.add_argument("--authority-id", required=True); command.add_argument("--authority-class", choices=["POLICY", "CONTROLLER"], required=True)
    command = _stored(commands, "causal-decision-add", "register a causal DecisionRecord with rejected alternatives and provenance", _causal_decision_add); command.add_argument("--input", required=True); command.add_argument("--activate", action="store_true")
    command = _stored(commands, "reactive-rule-add", "admit a reactive-obligation derivation rule without executing handlers", _reactive_rule_add); command.add_argument("--input", required=True); command.add_argument("--authority-id", required=True); command.add_argument("--authority-class", choices=["POLICY", "CONTROLLER"], required=True)
    command = _stored(commands, "reactive-derive", "derive ordinary obligations from durable event matches", _reactive_derive); command.add_argument("--from-sequence", type=int, default=0)
    _stored(commands, "reactive-obligations", "inspect reactive rules and derived obligations", _reactive_obligations)
    command = _stored(commands, "truth-maintain", "record and apply descendant-only truth maintenance", _truth_maintain); _node_args(command); command.add_argument("--reason", required=True); command.add_argument("--evidence-id", action="append"); command.add_argument("--authority-id", required=True); command.add_argument("--authority-class", choices=["VERIFIER", "POLICY", "CONTROLLER"], required=True)
    command = _stored(commands, "truth-resume", "resume a recorded but incomplete truth-maintenance plan", _truth_resume); command.add_argument("plan_id")
    _stored(commands, "truth-maintenance-report", "inspect recorded, applied, and pending truth-maintenance plans", _truth_report)
    _stored(commands, "semantic-memory-signals", "project deterministic V0.40 memory/context selection inputs", _memory_signals)
    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    for surface in ("dependencies", "semantic-dependencies", "truth-maintenance", "reactive-obligations", "semantic-memory-signals"):
        if surface not in choices: choices.append(surface)
    inspect._option_string_actions["--surface"].choices = choices
    return parser


def main(argv=None):
    parser = build_parser(); args = parser.parse_args(argv); return args.func(args)

if __name__ == "__main__": main()
