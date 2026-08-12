from __future__ import annotations

import json
from pathlib import Path

from . import cli_v29 as _v29
from .integrations.conformance import CONFORMANCE_SCENARIOS
from .integrations.conformance_registry import (
    list_conformance_drivers,
    run_adapter_conformance,
)
from .runtime_v30 import AASMEngine

# All inherited commands resume the current runtime implementation.
_v29._v28._v27._v25._v22._base.AASMEngine = AASMEngine


def _emit(value):
    print(json.dumps(value, indent=2, sort_keys=True))
    return value


def _adapter_conformance(args):
    report = run_adapter_conformance(
        args.adapter,
        scenarios=args.scenario or None,
        engine_class=AASMEngine,
    ).to_dict()
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _emit(report)
    if report["status"] == "FAIL":
        raise SystemExit(2)
    if report["status"] == "INCONCLUSIVE":
        raise SystemExit(3)
    return None


def _adapter_conformance_list(_args):
    _emit(
        {
            "contract_id": "aasm.adapter.conformance.v1",
            "drivers": list_conformance_drivers(),
            "required_scenarios": list(CONFORMANCE_SCENARIOS),
        }
    )
    return None


def build_parser():
    parser = _v29.build_parser()
    commands = _v29._v28._v27._v25._subparsers(parser)

    command = commands.add_parser(
        "adapter-conformance",
        help="run the framework-neutral AASM adapter conformance kit",
    )
    command.add_argument("--adapter", default="langgraph")
    command.add_argument(
        "--scenario",
        action="append",
        choices=list(CONFORMANCE_SCENARIOS),
        help="run only the selected scenario; repeat to select multiple",
    )
    command.add_argument("--output", help="write the JSON report to this path")
    command.set_defaults(func=_adapter_conformance)

    listing = commands.add_parser(
        "adapter-conformance-list",
        help="list built-in conformance drivers and required scenarios",
    )
    listing.set_defaults(func=_adapter_conformance_list)

    inspect = commands.choices["inspect"]
    choices = list(inspect._option_string_actions["--surface"].choices)
    if "adapter-conformance" not in choices:
        inspect._option_string_actions["--surface"].choices = [
            *choices,
            "adapter-conformance",
        ]
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
