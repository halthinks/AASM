from . import cli_v44 as _v44
from .convex_optimization import convex_optimization_contract
from .pulp_adapter import pulp_adapter_contract
from .modeling_conformance import run_modeling_conformance


def _json(value):
    _v44._json(value)


def _convex_contract(args):
    _json(convex_optimization_contract())


def _pulp_contract(args):
    _json(pulp_adapter_contract())


def _modeling_conformance(args):
    _json(run_modeling_conformance(real=args.real))


def build_parser():
    parser = _v44.build_parser()
    commands = _v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "convex-optimization-contract",
        help="show the v0.45 governed CVXPY convex optimization contract",
    ).set_defaults(func=_convex_contract)
    commands.add_parser(
        "pulp-adapter-contract",
        help="show the v0.45 PuLP translation-only adapter contract",
    ).set_defaults(func=_pulp_contract)
    command = commands.add_parser(
        "modeling-conformance",
        help="run CVXPY/PuLP conformance; --real executes installed modeling backends",
    )
    command.add_argument("--real", action="store_true")
    command.set_defaults(func=_modeling_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
