from . import cli_v47 as _v47
from .cross_run_conformance import run_cross_run_knowledge_conformance
from .cross_run_knowledge import cross_run_knowledge_contract


def _json(value):
    _v47._json(value)


def _cross_run_contract(args):
    _json(cross_run_knowledge_contract())


def _cross_run_conformance(args):
    _json(run_cross_run_knowledge_conformance())


def build_parser():
    parser = _v47.build_parser()
    commands = _v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser("cross-run-knowledge-contract", help="show the v0.48 governed cross-run knowledge contract").set_defaults(func=_cross_run_contract)
    commands.add_parser("cross-run-knowledge-conformance", help="run the v0.48 dependency-neutral cross-run knowledge conformance suite").set_defaults(func=_cross_run_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
