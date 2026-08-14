from . import cli_v49 as _v49
from .proof_claim_conformance import run_solver_proof_conformance
from .proof_claims import solver_proof_contract


def _json(value):
    _v49._json(value)


def _solver_proof_contract(args):
    _json(solver_proof_contract())


def _solver_proof_conformance(args):
    _json(run_solver_proof_conformance())


def build_parser():
    parser = _v49.build_parser()
    commands = _v49._v48._v47._v46._v45._v44._v43._v42._v41._v40._v39._v38._v37._v32._v31._v30._v29._v28._v27._v25._subparsers(parser)
    commands.add_parser(
        "solver-proof-contract",
        help="show the v0.50 proof-carrying solver claim contract",
    ).set_defaults(func=_solver_proof_contract)
    commands.add_parser(
        "solver-proof-conformance",
        help="run v0.50 proof-claim conformance and adversarial checks",
    ).set_defaults(func=_solver_proof_conformance)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
