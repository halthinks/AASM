from . import cli_v52 as _v52
from ._runtime_v53_authority import scoped_authority_runtime_contract
from ._runtime_v53_solver_learning import solver_learning_runtime_contract
from .scoped_authority import scoped_authority_contract
from .scoped_store import scoped_store_contract
from .solver_learning import solver_learning_contract


def _json(value):
    _v52._json(value)


def _scoped_authority_contract(args):
    _json(scoped_authority_contract())


def _scoped_authority_runtime_contract(args):
    _json(scoped_authority_runtime_contract())


def _scoped_store_contract(args):
    _json(scoped_store_contract())


def _solver_learning_contract(args):
    _json(solver_learning_contract())


def _solver_learning_runtime_contract(args):
    _json(solver_learning_runtime_contract())


def build_parser():
    parser = _v52.build_parser()
    commands = _v52._v51._v50._v49._v48._v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "scoped-authority-contract",
        help="show the pre-release v0.53 scoped identity/authority contract",
    ).set_defaults(func=_scoped_authority_contract)
    commands.add_parser(
        "scoped-authority-runtime-contract",
        help="show the pre-release v0.53 durable authority runtime contract",
    ).set_defaults(func=_scoped_authority_runtime_contract)
    commands.add_parser(
        "scoped-store-contract",
        help="show the pre-release v0.53 scope-safe persistence contract",
    ).set_defaults(func=_scoped_store_contract)
    commands.add_parser(
        "solver-learning-contract",
        help="show the pre-release v0.53 solver learning contract",
    ).set_defaults(func=_solver_learning_contract)
    commands.add_parser(
        "solver-learning-runtime-contract",
        help="show the pre-release v0.53 cross-run solver learning runtime contract",
    ).set_defaults(func=_solver_learning_runtime_contract)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
