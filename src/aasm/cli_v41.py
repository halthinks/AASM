from . import cli_v40 as _v40
from .runtime_v41 import AASMEngine
from .reuse_model import CanonicalRef,ReuseCandidate,ReuseRequest,reuse_contract
from .reuse_metrics import ReuseMetrics
from .solver_loop import solver_loop_contract
from .solver_types import SolverStepRequest

_v40.AASMEngine=AASMEngine

def _json(v): _v40._json(v)
def _load(p): return _v40._load(p)
def _with_engine(a,f): return _v40._with_engine(a,f)
def _stored(c,n,h,f): return _v40._stored(c,n,h,f)
def _reuse_contract(args): _json(reuse_contract())
def _solver_contract(args): _json(solver_loop_contract())
def _reuse_report(args): _with_engine(args,lambda e:_json(e.reuse_report()))
def _candidate(args):
    raw=_load(args.input); source=CanonicalRef(**raw.pop("source")); candidate=ReuseCandidate(source=source,**raw)
    _with_engine(args,lambda e:_json(e.register_reuse_candidate(candidate,authority_id=args.authority_id,authority_class=args.authority_class)))
def _lookup(args):
    request=ReuseRequest(**_load(args.input))
    def action(e):
        result=e.lookup_reuse(request)
        if args.commit and result["hit"]: result["committed"]=e.commit_reuse_certificate(result,actor_id=args.actor_id,authority_class=args.authority_class)
        _json(result)
    _with_engine(args,action)
def _metrics(args): _with_engine(args,lambda e:_json(e.record_reuse_metrics(ReuseMetrics(**_load(args.input)),actor_id=args.actor_id)))
def _solver_step(args):
    request=SolverStepRequest(**_load(args.input)); reuse=ReuseRequest(**_load(args.reuse_input)) if args.reuse_input else None
    _with_engine(args,lambda e:_json(e.solver_step(request,reuse_request=reuse)))

def build_parser():
    parser=_v40.build_parser(); commands=_v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("reuse-contract",help="show v0.41 reuse contract").set_defaults(func=_reuse_contract)
    commands.add_parser("solver-loop-contract",help="show v0.41 solver loop contract").set_defaults(func=_solver_contract)
    _stored(commands,"reuse-report","inspect reusable work",_reuse_report)
    c=_stored(commands,"reuse-candidate-add","index canonical prior work",_candidate); c.add_argument("--input",required=True); c.add_argument("--authority-id",required=True); c.add_argument("--authority-class",choices=["POLICY","CONTROLLER"],required=True)
    c=_stored(commands,"reuse-lookup","validate reusable prior work",_lookup); c.add_argument("--input",required=True); c.add_argument("--commit",action="store_true"); c.add_argument("--actor-id",default="cli"); c.add_argument("--authority-class",choices=["POLICY","CONTROLLER"],default="CONTROLLER")
    c=_stored(commands,"reuse-metrics-record","record reuse metrics",_metrics); c.add_argument("--input",required=True); c.add_argument("--actor-id",required=True)
    c=_stored(commands,"solver-step","evaluate one solver-loop step",_solver_step); c.add_argument("--input",required=True); c.add_argument("--reuse-input")
    return parser

def main(argv=None):
    parser=build_parser(); args=parser.parse_args(argv); return args.func(args)
