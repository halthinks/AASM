from . import cli_v51 as _v51
from .multi_objective import frontier_contract, multi_objective_contract
from .resource_routing import (
    RESOURCE_ROUTING_CONTRACT_ID,
    RESOURCE_ROUTING_CONTRACT_VERSION,
    RESOURCE_ROUTING_STABILITY,
    default_resource_routing_objectives,
)


def _json(value):
    _v51._json(value)


def _multi_objective_contract(args):
    _json(multi_objective_contract())


def _pareto_frontier_contract(args):
    _json(frontier_contract())


def _resource_routing_contract(args):
    _json({
        "contract_id": RESOURCE_ROUTING_CONTRACT_ID,
        "contract_version": RESOURCE_ROUTING_CONTRACT_VERSION,
        "stability": RESOURCE_ROUTING_STABILITY,
        "default_objectives": [row.to_dict() for row in default_resource_routing_objectives()],
        "candidate_frontier_scope": "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY",
        "result_authority": "EVIDENCE_ONLY",
        "resource_state_authority": "NEVER_GRANTS_AUTHORITY",
    })


def build_parser():
    parser = _v51.build_parser()
    commands = _v51._v50._v49._v48._v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "multi-objective-contract",
        help="show the pre-release v0.52 multi-objective contract",
    ).set_defaults(func=_multi_objective_contract)
    commands.add_parser(
        "pareto-frontier-contract",
        help="show the pre-release v0.52 Pareto frontier contract",
    ).set_defaults(func=_pareto_frontier_contract)
    commands.add_parser(
        "resource-routing-contract",
        help="show the pre-release v0.52 governed resource-routing objective contract",
    ).set_defaults(func=_resource_routing_contract)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
