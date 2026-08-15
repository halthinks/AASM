import argparse

from . import cli_v53 as _v53
from .effects import effect_governance_contract
from .runtime_v54 import effect_governance_runtime_contract, solver_portfolio_contract
from .runtime_v54_exchange import solver_exchange_contract
from .runtime_v54_portfolio import solver_portfolio_runtime_contract


def _json(value):
    _v53._json(value)


def build_parser():
    parser = _v53.build_parser()
    commands = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    commands.add_parser(
        "effect-governance-contract",
        help="show the pre-release v0.54 effect intent/ownership/reconciliation contract",
    ).set_defaults(func=lambda args: _json(effect_governance_contract()))
    commands.add_parser(
        "effect-governance-runtime-contract",
        help="show the pre-release v0.54 governed effect runtime contract",
    ).set_defaults(func=lambda args: _json(effect_governance_runtime_contract()))
    commands.add_parser(
        "solver-portfolio-contract",
        help="show the pre-release v0.54 deterministic solver portfolio contract",
    ).set_defaults(func=lambda args: _json(solver_portfolio_contract()))
    commands.add_parser(
        "solver-portfolio-runtime-contract",
        help="show the pre-release v0.54 governed portfolio execution contract",
    ).set_defaults(func=lambda args: _json(solver_portfolio_runtime_contract()))
    commands.add_parser(
        "solver-exchange-contract",
        help="show the pre-release v0.54 certified cross-solver exchange contract",
    ).set_defaults(func=lambda args: _json(solver_exchange_contract()))
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
