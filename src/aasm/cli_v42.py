from . import cli_v41 as _v41
from .reference_domains import REFERENCE_DOMAIN_IDS, reference_domain_contract, run_reference_domain_stress


def _json(value):
    _v41._json(value)


def _reference_contract(args):
    _json(reference_domain_contract())


def _reference_stress(args):
    _json(run_reference_domain_stress(args.domain))


def build_parser():
    parser = _v41.build_parser()
    commands = _v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "reference-domain-contract",
        help="show the v0.42 offline reference-domain stress contract",
    ).set_defaults(func=_reference_contract)
    command = commands.add_parser(
        "reference-domain-stress",
        help="run v0.42 reference-domain stress scenarios",
    )
    command.add_argument("--domain", choices=REFERENCE_DOMAIN_IDS)
    command.set_defaults(func=_reference_stress)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
