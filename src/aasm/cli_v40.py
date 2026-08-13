from __future__ import annotations

import json
from pathlib import Path

from . import cli_v39 as _v39
from .runtime_v40 import AASMEngine
from .hierarchical_memory import ContextProjectionRequest, MemoryIndexEntry, hierarchical_memory_contract
from .memory_conformance import run_hierarchical_memory_conformance

_v39.AASMEngine = AASMEngine
_v39._v38.AASMEngine = AASMEngine
_v39._v38._v37.AASMEngine = AASMEngine
_v39._v38._v37._v32.AASMEngine = AASMEngine
_v39._v38._v37._v32._v31.AASMEngine = AASMEngine
_v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine

def _json(value): _v39._json(value)
def _with_engine(args, callback): return _v39._with_engine(args, callback)
def _stored(commands, name, help_text, func): return _v39._stored(commands, name, help_text, func)
def _load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def _authority(command): command.add_argument("--authority-id", required=True); command.add_argument("--authority-class", choices=["POLICY", "CONTROLLER"], required=True)
def _contract(args): _json(hierarchical_memory_contract())
def _conformance(args): _json(run_hierarchical_memory_conformance())
def _report(args): _with_engine(args, lambda e: _json(e.hierarchical_memory_report(as_of=args.as_of)))
def _propose(args):
    payload = _load(args.input); operation = str(payload.pop("operation")); _with_engine(args, lambda e: _json(e.propose_memory_operation(operation, **payload)))
def _authorize(args): _with_engine(args, lambda e: _json(e.authorize_memory_operation(args.decision_id, authority_id=args.authority_id, authority_class=args.authority_class)))
def _commit(args): _with_engine(args, lambda e: _json(e.commit_memory_operation(args.decision_id, worker_id=args.worker_id, result_metadata=_load(args.result_metadata) if args.result_metadata else None)))
def _forget(args):
    def action(e):
        proposed = e.propose_memory_forget(args.memory_id, proposer_id=args.proposer_id, reason=args.reason, mode=args.mode)
        if args.authorize:
            proposed["authorization"] = e.authorize_memory_operation(proposed["decision"]["decision_id"], authority_id=args.authority_id, authority_class=args.authority_class)
        _json(proposed)
    _with_engine(args, action)
def _index_add(args): _with_engine(args, lambda e: _json(e.admit_memory_index(MemoryIndexEntry.from_dict(_load(args.input)), authority_id=args.authority_id, authority_class=args.authority_class)))
def _request(path): return ContextProjectionRequest(**_load(path))
def _frontier(args): _with_engine(args, lambda e: _json(e.reasoning_frontier(_request(args.input))))
def _context(args): _with_engine(args, lambda e: _json(e.context_projection(_request(args.input))))
def _context_record(args): _with_engine(args, lambda e: _json(e.record_context_projection(_request(args.input), actor_id=args.actor_id)))

def build_parser():
    parser = _v39.build_parser(); commands = _v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("hierarchical-memory-contract", help="show v0.40 memory/context contracts").set_defaults(func=_contract)
    commands.add_parser("hierarchical-memory-conformance", help="run v0.40 memory/context conformance").set_defaults(func=_conformance)
    c=_stored(commands,"memory-report","inspect hierarchical memory",_report); c.add_argument("--as-of",type=float)
    c=_stored(commands,"memory-propose","propose governed memory operation",_propose); c.add_argument("--input",required=True)
    c=_stored(commands,"memory-authorize","authorize memory operation",_authorize); c.add_argument("decision_id"); _authority(c)
    c=_stored(commands,"memory-commit","commit authorized memory",_commit); c.add_argument("decision_id"); c.add_argument("--worker-id",required=True); c.add_argument("--result-metadata")
    c=_stored(commands,"memory-forget","propose tombstone forgetting",_forget); c.add_argument("memory_id"); c.add_argument("--proposer-id",required=True); c.add_argument("--reason",required=True); c.add_argument("--mode",choices=["VISIBILITY_REVOKED","CRYPTO_ERASURE_REQUESTED","RETENTION_EXPIRED"],default="VISIBILITY_REVOKED"); c.add_argument("--authorize",action="store_true"); c.add_argument("--authority-id"); c.add_argument("--authority-class",choices=["POLICY","CONTROLLER"])
    c=_stored(commands,"memory-index-add","admit derived memory index",_index_add); c.add_argument("--input",required=True); _authority(c)
    c=_stored(commands,"reasoning-frontier","project bounded reasoning frontier",_frontier); c.add_argument("--input",required=True)
    c=_stored(commands,"context-project","project bounded memory+reasoning context",_context); c.add_argument("--input",required=True)
    c=_stored(commands,"context-record","record context projection as Evidence",_context_record); c.add_argument("--input",required=True); c.add_argument("--actor-id",required=True)
    inspect=commands.choices["inspect"]; choices=list(inspect._option_string_actions["--surface"].choices)
    for s in ("hierarchical-memory","memory-hierarchy","reasoning-frontier","context-projection","hierarchical-memory-contract","context-projection-contract"):
        if s not in choices: choices.append(s)
    inspect._option_string_actions["--surface"].choices=choices
    return parser

def main(argv=None):
    parser=build_parser(); args=parser.parse_args(argv)
    if getattr(args,"authorize",False) and (not getattr(args,"authority_id",None) or not getattr(args,"authority_class",None)): parser.error("memory-forget --authorize requires --authority-id and --authority-class")
    return args.func(args)

if __name__ == "__main__": main()
