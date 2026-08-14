from . import cli_v43 as _v43
from .optimization import optimization_blueprint, optimization_contract
from .optimization_conformance import run_optimization_conformance


def _json(value):
    _v43._json(value)


def _optimization_contract(args):
    _json(optimization_contract())


def _optimization_blueprint(args):
    _json(optimization_blueprint())


def _optimization_conformance(args):
    _json(run_optimization_conformance(real=args.real))


def build_parser():
    parser = _v43.build_parser()
    commands = _v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "optimization-contract",
        help="show the v0.44 SAT/CP-SAT/MILP portfolio contract",
    ).set_defaults(func=_optimization_contract)
    commands.add_parser(
        "optimization-blueprint",
        help="show default optimization capabilities and providers",
    ).set_defaults(func=_optimization_blueprint)
    command = commands.add_parser(
        "optimization-conformance",
        help="run optimization IR conformance; --real executes installed native backends",
    )
    command.add_argument("--real", action="store_true")
    command.set_defaults(func=_optimization_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
