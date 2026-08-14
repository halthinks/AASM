from . import cli_v48 as _v48
from .public_v49 import public_api_contract
from .runtime_v49 import AASMEngine
from .semantic_solver_rc import (
    build_semantic_solver_rc_freeze_manifest,
    run_claim_gate_audit,
    run_cross_backend_overlap_certification,
    run_rc_benchmarks,
    run_semantic_solver_rc_certification,
    run_upgrade_compatibility,
    semantic_solver_rc_contract,
)


def _json(value):
    _v48._json(value)


def _rc_contract(args):
    _json(semantic_solver_rc_contract())


def _rc_freeze(args):
    _json(build_semantic_solver_rc_freeze_manifest(public_api_contract()))


def _rc_upgrade(args):
    _json(run_upgrade_compatibility(target_engine_cls=AASMEngine))


def _rc_cross_backend(args):
    _json(run_cross_backend_overlap_certification(real=bool(args.real)))


def _rc_benchmark(args):
    _json(run_rc_benchmarks(real=bool(args.real), target_engine_cls=AASMEngine, iterations=int(args.iterations)))


def _rc_claim_audit(args):
    _json(run_claim_gate_audit())


def _rc_certify(args):
    _json(run_semantic_solver_rc_certification(real=bool(args.real), target_engine_cls=AASMEngine, public_contract=public_api_contract()))


def build_parser():
    parser = _v48.build_parser()
    commands = _v48._v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("semantic-solver-rc-contract", help="show the v0.49 semantic solver release-candidate contract").set_defaults(func=_rc_contract)
    commands.add_parser("semantic-solver-rc-freeze", help="emit the v0.49 public contract freeze manifest").set_defaults(func=_rc_freeze)
    commands.add_parser("semantic-solver-rc-upgrade", help="run v0.41/v0.47/v0.48 replay and upgrade compatibility fixtures").set_defaults(func=_rc_upgrade)
    overlap = commands.add_parser("semantic-solver-rc-cross-backend", help="certify overlapping SAT/CP-SAT/MILP semantics without voting")
    overlap.add_argument("--real", action="store_true", help="execute native CaDiCaL, OR-Tools CP-SAT, and HiGHS backends")
    overlap.set_defaults(func=_rc_cross_backend)
    benchmark = commands.add_parser("semantic-solver-rc-benchmark", help="measure RC orchestration workloads without making ungated speedup claims")
    benchmark.add_argument("--real", action="store_true", help="include direct native and full leased CP-SAT lifecycle measurements")
    benchmark.add_argument("--iterations", type=int, default=64)
    benchmark.set_defaults(func=_rc_benchmark)
    commands.add_parser("semantic-solver-rc-claim-audit", help="audit public capability claims against reproducible repository gates").set_defaults(func=_rc_claim_audit)
    certify = commands.add_parser("semantic-solver-rc-certify", help="run the complete v0.49 RC certification suite")
    certify.add_argument("--real", action="store_true", help="include the complete native optimization/modeling/advanced portfolio")
    certify.set_defaults(func=_rc_certify)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
