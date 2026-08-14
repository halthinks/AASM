from contextlib import redirect_stdout
import io

from . import cli_v45 as _v45
from .advanced_optimization import advanced_optimization_blueprint, advanced_optimization_contract
from .advanced_optimization_conformance import run_advanced_optimization_conformance


def _json(value):
    _v45._json(value)


def _advanced_contract(args):
    _json(advanced_optimization_contract())


def _advanced_blueprint(args):
    _json(advanced_optimization_blueprint())


def _advanced_conformance(args):
    # Native solver libraries may emit incidental stdout. Preserve a strict
    # machine-readable CLI by capturing backend chatter internally.
    with redirect_stdout(io.StringIO()):
        report = run_advanced_optimization_conformance(real=args.real)
    _json(report)


def build_parser():
    parser = _v45.build_parser()
    commands = _v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "advanced-optimization-contract",
        help="show the v0.46 advanced solver control/search-artifact contract",
    ).set_defaults(func=_advanced_contract)
    commands.add_parser(
        "advanced-optimization-blueprint",
        help="show v0.46 advanced solver capabilities and providers",
    ).set_defaults(func=_advanced_blueprint)
    command = commands.add_parser(
        "advanced-optimization-conformance",
        help="run v0.46 advanced solver conformance; --real executes installed native backends",
    )
    command.add_argument("--real", action="store_true")
    command.set_defaults(func=_advanced_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
