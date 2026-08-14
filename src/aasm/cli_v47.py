from . import cli_v46 as _v46
from .sii_governance import default_sii_scoring_policy, governed_sii_contract


def _json(value):
    _v46._json(value)


def _sii_governance_contract(args):
    _json(governed_sii_contract())


def _sii_default_policy(args):
    _json(default_sii_scoring_policy().to_dict())


def build_parser():
    parser = _v46.build_parser()
    commands = _v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "sii-governance-contract",
        help="show the v0.47 governed SII contract",
    ).set_defaults(func=_sii_governance_contract)
    commands.add_parser(
        "sii-default-scoring-policy",
        help="show the v0.47 default versioned SII scoring/resource policy",
    ).set_defaults(func=_sii_default_policy)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
