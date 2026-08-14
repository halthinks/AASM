from . import cli_v50 as _v50
from .solution_pool_conformance import run_solution_pool_conformance
from .solution_pools import enumeration_contract, solution_pool_contract


def _json(value):
    _v50._json(value)


def _solution_pool_contract(args):
    _json(solution_pool_contract())


def _enumeration_contract(args):
    _json(enumeration_contract())


def _solution_pool_conformance(args):
    _json(run_solution_pool_conformance(real_backends=bool(args.real)))


def build_parser():
    parser = _v50.build_parser()
    commands = _v50._v49._v48._v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "solution-pool-contract",
        help="show the v0.51 governed solution-pool contract",
    ).set_defaults(func=_solution_pool_contract)
    commands.add_parser(
        "enumeration-contract",
        help="show the v0.51 complete finite enumeration contract",
    ).set_defaults(func=_enumeration_contract)
    conformance = commands.add_parser(
        "solution-pool-conformance",
        help="run v0.51 solution-pool and enumeration conformance",
    )
    conformance.add_argument("--real", action="store_true", help="exercise real CP-SAT and HiGHS enumeration")
    conformance.set_defaults(func=_solution_pool_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
