from __future__ import annotations

import argparse
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import json
import os
from pathlib import Path
import re
import tarfile
import tomllib
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.\-]+)?)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM_FILENAME = "SHA256SUMS.txt"
MANIFEST_FILENAME = "release-manifest.json"
REQUIRED_WHEEL_MEMBERS = {
    "aasm/__init__.py",
    "aasm/operator_runbooks.py",
    "aasm/reference_data/research/manifest.json",
}


def project_metadata(root: Path = ROOT) -> dict[str, Any]:
    with (root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    project = dict(data["project"])
    return {
        "name": str(project["name"]),
        "version": str(project["version"]),
        "requires_python": str(project.get("requires-python", "")),
    }


def project_version(root: Path = ROOT) -> str:
    return project_metadata(root)["version"]


def verify_tag(tag: str, version: str | None = None) -> dict[str, Any]:
    version = version or project_version()
    match = TAG_RE.fullmatch(tag)
    valid = bool(match and match.group("version") == version)
    return {
        "valid": valid,
        "tag": tag,
        "expected_tag": f"v{version}",
        "version": version,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release_files(dist_dir: Path) -> list[Path]:
    if not dist_dir.is_dir():
        raise FileNotFoundError(dist_dir)
    rows = sorted(
        path
        for path in dist_dir.iterdir()
        if path.is_file()
        and (path.suffix == ".whl" or path.name.endswith(".tar.gz"))
    )
    if not rows:
        raise ValueError(f"no wheel or source distribution found in {dist_dir}")
    return rows


def build_manifest(
    dist_dir: Path,
    *,
    commit_sha: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    metadata = project_metadata(root)
    files = release_files(dist_dir)
    return {
        "schema_version": 1,
        "package": metadata["name"],
        "version": metadata["version"],
        "tag": f"v{metadata['version']}",
        "commit_sha": commit_sha or os.getenv("GITHUB_SHA") or None,
        "files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }


def write_release_manifests(
    dist_dir: Path,
    *,
    checksums_path: Path,
    json_path: Path,
    commit_sha: str | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    manifest = build_manifest(dist_dir, commit_sha=commit_sha, root=root)
    checksums_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    checksums_path.write_text(
        "".join(
            f"{row['sha256']}  {row['name']}\n"
            for row in manifest["files"]
        ),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _canonical_package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def verify_wheel(
    wheel_path: Path,
    *,
    expected_version: str | None = None,
    expected_name: str | None = None,
) -> dict[str, Any]:
    expected_version = expected_version or project_version()
    expected_name = expected_name or project_metadata()["name"]
    errors: list[str] = []
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
        metadata_names = sorted(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        if len(metadata_names) != 1:
            errors.append(
                f"expected exactly one dist-info/METADATA entry, found {metadata_names}"
            )
            package_name = version = None
        else:
            message = BytesParser(policy=email_policy).parsebytes(
                archive.read(metadata_names[0])
            )
            package_name = str(message.get("Name") or "")
            version = str(message.get("Version") or "")
            if _canonical_package_name(package_name) != _canonical_package_name(
                expected_name
            ):
                errors.append(
                    f"wheel package name {package_name!r} does not match {expected_name!r}"
                )
            if version != expected_version:
                errors.append(
                    f"wheel version {version!r} does not match {expected_version!r}"
                )
        missing = sorted(REQUIRED_WHEEL_MEMBERS - names)
        if missing:
            errors.append(f"wheel is missing required members: {missing}")
    return {
        "valid": not errors,
        "wheel": str(wheel_path),
        "package": package_name,
        "version": version,
        "sha256": sha256_file(wheel_path),
        "errors": errors,
    }


def verify_sdist(
    sdist_path: Path,
    *,
    expected_version: str | None = None,
) -> dict[str, Any]:
    expected_version = expected_version or project_version()
    errors: list[str] = []
    with tarfile.open(sdist_path, "r:gz") as archive:
        names = archive.getnames()
    roots = {name.split("/", 1)[0] for name in names if name}
    if len(roots) != 1:
        errors.append(f"source distribution has unexpected roots: {sorted(roots)}")
    expected_root = f"aasm_runtime-{expected_version}"
    root = next(iter(roots), None)
    if root != expected_root:
        errors.append(f"source root {root!r} does not match {expected_root!r}")
    required_suffixes = {
        "pyproject.toml",
        "README.md",
        "src/aasm/operator_runbooks.py",
        "src/aasm/reference_data/research/manifest.json",
    }
    missing = [
        suffix
        for suffix in sorted(required_suffixes)
        if not any(name.endswith("/" + suffix) for name in names)
    ]
    if missing:
        errors.append(f"source distribution is missing: {missing}")
    return {
        "valid": not errors,
        "sdist": str(sdist_path),
        "root": root,
        "sha256": sha256_file(sdist_path),
        "errors": errors,
    }


def verify_release_history(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    releases = list(data.get("releases") or [])
    seen_tags: set[str] = set()
    seen_commits: set[str] = set()
    for index, row in enumerate(releases):
        tag = str(row.get("tag") or "")
        commit = str(row.get("commit") or "")
        title = str(row.get("title") or "")
        if not TAG_RE.fullmatch(tag):
            errors.append(f"release {index} has invalid tag {tag!r}")
        if tag in seen_tags:
            errors.append(f"duplicate release tag {tag}")
        if not SHA_RE.fullmatch(commit):
            errors.append(f"release {tag or index} has invalid commit SHA {commit!r}")
        if commit in seen_commits:
            errors.append(f"duplicate release commit {commit}")
        if not title:
            errors.append(f"release {tag or index} has no title")
        seen_tags.add(tag)
        seen_commits.add(commit)
    return {
        "valid": not errors,
        "schema_version": data.get("schema_version"),
        "release_count": len(releases),
        "releases": releases,
        "errors": errors,
    }


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

    manifest = commands.add_parser(
        "manifest",
        help="write SHA-256 and JSON manifests for wheel/sdist artifacts",
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

    args = parser.parse_args(argv)
    if args.command == "version":
        _print(project_version())
        return 0
    if args.command == "verify-tag":
        result = verify_tag(args.tag)
    elif args.command == "verify-history":
        result = verify_release_history(args.path)
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
    else:
        raise AssertionError(args.command)
    _print(result)
    return 0 if result.get("valid", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
