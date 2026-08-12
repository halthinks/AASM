from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from release_artifacts_core import (
    compare_builds,
    project_version,
    verify_release_history,
    verify_sdist,
    verify_tag,
    verify_wheel,
    write_release_manifests,
)
from release_artifacts_github import (
    verify_github_release,
    write_historical_release_report,
)

def _print(value: Any) -> None:
    if isinstance(value, str):
        print(value)
    else:
        print(json.dumps(value, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build and verify immutable AASM release artifacts."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("version", help="print the project version")

    tag = commands.add_parser("verify-tag", help="verify a vVERSION release tag")
    tag.add_argument("tag")

    history = commands.add_parser(
        "verify-history",
        help="validate the maintained historical release-tag map",
    )
    history.add_argument("path", type=Path)

    compare = commands.add_parser(
        "compare-builds",
        help="require two independent distribution builds to be byte-identical",
    )
    compare.add_argument("left_dir", type=Path)
    compare.add_argument("right_dir", type=Path)

    historical = commands.add_parser(
        "historical-report",
        help="report historical tag state without attempting privileged backfill",
    )
    historical.add_argument("path", type=Path)
    historical.add_argument("--repository", required=True)
    historical.add_argument("--output", type=Path, required=True)
    historical.add_argument("--release-commit")

    manifest = commands.add_parser(
        "manifest",
        help="write SHA-256 and JSON manifests for release inputs",
    )
    manifest.add_argument("dist_dir", type=Path)
    manifest.add_argument("--checksums", type=Path, required=True)
    manifest.add_argument("--json", dest="json_path", type=Path, required=True)
    manifest.add_argument("--commit-sha")

    wheel = commands.add_parser("verify-wheel", help="inspect a built wheel")
    wheel.add_argument("wheel", type=Path)
    wheel.add_argument("--expected-version")
    wheel.add_argument("--expected-name")

    sdist = commands.add_parser("verify-sdist", help="inspect a source distribution")
    sdist.add_argument("sdist", type=Path)
    sdist.add_argument("--expected-version")

    github_release = commands.add_parser(
        "verify-github-release",
        help="verify the immutable remote release tag and exact asset bytes",
    )
    github_release.add_argument("tag")
    github_release.add_argument("dist_dir", type=Path)
    github_release.add_argument("--repository", required=True)
    github_release.add_argument("--expected-commit", required=True)

    args = parser.parse_args(argv)
    if args.command == "version":
        _print(project_version())
        return 0
    if args.command == "verify-tag":
        result = verify_tag(args.tag)
    elif args.command == "verify-history":
        result = verify_release_history(args.path)
    elif args.command == "compare-builds":
        result = compare_builds(args.left_dir, args.right_dir)
    elif args.command == "historical-report":
        result = write_historical_release_report(
            args.path,
            repository=args.repository,
            output_path=args.output,
            release_commit=args.release_commit,
        )
    elif args.command == "manifest":
        result = write_release_manifests(
            args.dist_dir,
            checksums_path=args.checksums,
            json_path=args.json_path,
            commit_sha=args.commit_sha,
        )
    elif args.command == "verify-wheel":
        result = verify_wheel(
            args.wheel,
            expected_version=args.expected_version,
            expected_name=args.expected_name,
        )
    elif args.command == "verify-sdist":
        result = verify_sdist(
            args.sdist,
            expected_version=args.expected_version,
        )
    elif args.command == "verify-github-release":
        result = verify_github_release(
            args.tag,
            args.dist_dir,
            repository=args.repository,
            expected_commit=args.expected_commit,
        )
    else:
        raise AssertionError(args.command)
    _print(result)
    return 0 if result.get("valid", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
