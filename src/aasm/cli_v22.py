from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import cli_v19 as _base
from .cli_v21 import build_parser as build_v21_parser
from .domain_adapters import CandidateModel
from .profile_conformance import ProfileConformanceKit
from .profile_packages import (
    AASMPackageManifest,
    AASMProfile,
    ProfileEvolutionProposal,
    ProfileMigration,
)
from .research_profile import ResearchProfileRegistry
from .runtime_v22 import AASMEngine
from .semantic_result import SemanticResultEnvelope

# All inherited CLI handlers resolve AASMEngine from cli_v19's module globals.
# Upgrade that global rather than duplicating the established command surface.
_base.AASMEngine = AASMEngine


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    raise RuntimeError("AASM CLI parser has no subparser action")


def _json(value):
    _base._json(value)


def _load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _registry(discover: bool = False) -> ResearchProfileRegistry:
    registry = ResearchProfileRegistry(include_builtins=True)
    if discover:
        registry.discover()
    return registry


def _profile_list(args):
    _json({"profiles": _registry(args.discover).list_profiles()})


def _profile_describe(args):
    profile = _registry(args.discover).resolve(args.profile)
    _json({"profile": profile.to_dict(), "fingerprint": profile.fingerprint})


def _profile_validate(args):
    profile = AASMProfile.load(args.path)
    _json({"valid": True, "profile": profile.to_dict(), "fingerprint": profile.fingerprint})


def _package_validate(args):
    package = AASMPackageManifest.load(args.path)
    _json({"valid": True, "package": package.to_dict(), "fingerprint": package.fingerprint})


def _profile_conformance(args):
    profile = AASMProfile.load(args.path)
    package = AASMPackageManifest.load(args.package) if args.package else None
    report = ProfileConformanceKit().run(profile, package=package)
    _json(report.to_dict())
    if not report.valid:
        raise SystemExit(2)


def _semantic_validate(args):
    result = SemanticResultEnvelope.from_dict(_load(args.path))
    ok, detail = ProfileConformanceKit().semantic_roundtrip(result)
    _json({"valid": ok, "error": detail, "result": result.to_dict(), "fingerprint": result.fingerprint})
    if not ok:
        raise SystemExit(2)


def _profile_report(args):
    _base._with_engine(args, lambda engine: _json(engine.profile_report()))


def _profile_bind(args):
    profile = _registry(args.discover).resolve(args.profile)
    package = AASMPackageManifest.load(args.package) if args.package else None
    configuration = _load(args.config) if args.config else {}
    migration = ProfileMigration.from_dict(_load(args.migration)) if args.migration else None
    _base._with_engine(
        args,
        lambda engine: _json(
            engine.bind_profile(
                profile,
                package=package,
                configuration=configuration,
                actor=args.actor,
                migration=migration,
            )
        ),
    )


def _profile_evolution_propose(args):
    proposal = ProfileEvolutionProposal.from_dict(_load(args.proposal))
    _base._with_engine(args, lambda engine: _json(engine.propose_profile_evolution(proposal)))


def _profile_evolution_activate(args):
    profile = _registry(args.discover).resolve(args.profile)
    package = AASMPackageManifest.load(args.package) if args.package else None
    migration = ProfileMigration.from_dict(_load(args.migration))
    configuration = _load(args.config) if args.config else {}
    _base._with_engine(
        args,
        lambda engine: _json(
            engine.activate_profile_evolution(
                args.proposal_id,
                profile,
                migration,
                package=package,
                configuration=configuration,
                actor=args.actor,
            )
        ),
    )


def _candidate_validate(args):
    candidate = CandidateModel.from_dict(_load(args.candidate))
    _base._with_engine(
        args,
        lambda engine: _json(engine.validate_candidate_model(candidate).to_dict()),
    )


def _decision_request(args):
    _base._with_engine(args, lambda engine: _json(engine.decision_request().to_dict()))


def _semantic_record(args):
    result = SemanticResultEnvelope.from_dict(_load(args.result))
    _base._with_engine(args, lambda engine: _json(engine.record_semantic_result(result)))


def _semantic_results(args):
    _base._with_engine(
        args,
        lambda engine: _json(
            {
                "results": engine.semantic_results_report(
                    classification=args.classification,
                    subject_id=args.subject_id,
                    limit=args.limit,
                )
            }
        ),
    )


def build_parser():
    parser = build_v21_parser()
    commands = _subparsers(parser)

    command = commands.add_parser("profiles", help="list built-in and installed domain-neutral profiles")
    command.add_argument("--discover", action="store_true", help="load already-installed aasm.profiles entry points")
    command.set_defaults(func=_profile_list)

    command = commands.add_parser("profile-describe", help="describe a profile ID, ID@version, or JSON path")
    command.add_argument("profile")
    command.add_argument("--discover", action="store_true")
    command.set_defaults(func=_profile_describe)

    command = commands.add_parser("profile-validate", help="validate a profile JSON document")
    command.add_argument("path")
    command.set_defaults(func=_profile_validate)

    command = commands.add_parser("package-validate", help="validate an AASM package manifest")
    command.add_argument("path")
    command.set_defaults(func=_package_validate)

    command = commands.add_parser("profile-conformance", help="run static profile/package conformance checks")
    command.add_argument("path")
    command.add_argument("--package")
    command.set_defaults(func=_profile_conformance)

    command = commands.add_parser("semantic-result-validate", help="validate the generic semantic-result envelope")
    command.add_argument("path")
    command.set_defaults(func=_semantic_validate)

    def stored(name: str, help_text: str, func):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("machine_id")
        _base._store_args(command)
        command.set_defaults(func=func)
        return command

    stored("profile", "inspect the profile bound to a machine", _profile_report)

    command = stored("profile-bind", "bind a profile package explicitly", _profile_bind)
    command.add_argument("--profile", required=True)
    command.add_argument("--package")
    command.add_argument("--config")
    command.add_argument("--migration")
    command.add_argument("--actor", default="controller")
    command.add_argument("--discover", action="store_true")

    command = stored("profile-evolution-propose", "record an evidence-backed profile revision proposal", _profile_evolution_propose)
    command.add_argument("--proposal", required=True)

    command = stored("profile-evolution-activate", "explicitly activate a conformance-tested profile revision", _profile_evolution_activate)
    command.add_argument("--proposal-id", required=True)
    command.add_argument("--profile", required=True)
    command.add_argument("--migration", required=True)
    command.add_argument("--package")
    command.add_argument("--config")
    command.add_argument("--actor", default="controller")
    command.add_argument("--discover", action="store_true")

    command = stored("candidate-validate", "validate a backend candidate without activating it", _candidate_validate)
    command.add_argument("--candidate", required=True)

    stored("decision-request", "emit the solver-neutral decision request", _decision_request)

    command = stored("semantic-result-record", "record a generic domain semantic result", _semantic_record)
    command.add_argument("--result", required=True)

    command = stored("semantic-results", "inspect recorded domain semantic results", _semantic_results)
    command.add_argument("--classification")
    command.add_argument("--subject-id")
    command.add_argument("--limit", type=int, default=200)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main()
