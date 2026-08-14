from . import cli_v42 as _v42
from .certification import CERTIFICATION_TARGET_IDS, certification_contract, run_certification
from .sii import sii_contract


def _json(value):
    _v42._json(value)


def _certification_contract(args):
    _json(certification_contract())


def _certify(args):
    _json(run_certification(args.target))


def _sii_contract(args):
    _json(sii_contract())


def build_parser():
    parser = _v42.build_parser()
    commands = _v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "certification-contract",
        help="show the v0.43 semantic/adversarial certification contract",
    ).set_defaults(func=_certification_contract)
    command = commands.add_parser(
        "certify",
        help="run v0.43 deterministic certification profiles",
    )
    command.add_argument("--target", choices=CERTIFICATION_TARGET_IDS)
    command.set_defaults(func=_certify)
    commands.add_parser(
        "sii-contract",
        help="show the experimental v0.44 SII participation-plane contract",
    ).set_defaults(func=_sii_contract)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
