from __future__ import annotations

import argparse
from collections.abc import Callable
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib
from typing import Any
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^v(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.\-]+)?)$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM_FILENAME = "SHA256SUMS.txt"
MANIFEST_FILENAME = "release-manifest.json"
HISTORICAL_REPORT_FILENAME = "historical-release-report.json"
REQUIRED_WHEEL_MEMBERS = {
    "aasm/__init__.py",
    "aasm/cli_v29.py",
    "aasm/integrations/__init__.py",
    "aasm/integrations/langgraph.py",
    "aasm/operator_runbooks.py",
    "aasm/reference_data/research/manifest.json",
    "aasm/runtime_v29.py",
}


class GitHubReleaseError(RuntimeError):
    """Raised when the GitHub release boundary cannot be verified."""


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


def distribution_files(dist_dir: Path) -> list[Path]:
    if not dist_dir.is_dir():
        raise FileNotFoundError(dist_dir)
    wheels = sorted(path for path in dist_dir.iterdir() if path.is_file() and path.suffix == ".whl")
    sdists = sorted(
        path for path in dist_dir.iterdir() if path.is_file() and path.name.endswith(".tar.gz")
    )
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError(
            f"expected one wheel and one source distribution in {dist_dir}; "
            f"found wheels={[path.name for path in wheels]} "
            f"sdists={[path.name for path in sdists]}"
        )
    return [*wheels, *sdists]


def release_files(dist_dir: Path) -> list[Path]:
    rows = distribution_files(dist_dir)
    historical_report = dist_dir / HISTORICAL_REPORT_FILENAME
    if historical_report.is_file():
        rows.append(historical_report)
    return sorted(rows, key=lambda path: path.name)


def release_assets(dist_dir: Path) -> list[Path]:
    if not dist_dir.is_dir():
        raise FileNotFoundError(dist_dir)
    rows = sorted(path for path in dist_dir.iterdir() if path.is_file())
    if not rows:
        raise ValueError(f"no release assets found in {dist_dir}")
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
        "schema_version": 2,
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
        "".join(f"{row['sha256']}  {row['name']}\n" for row in manifest["files"]),
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
    package_name: str | None = None
    version: str | None = None
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
        metadata_names = sorted(name for name in names if name.endswith(".dist-info/METADATA"))
        if len(metadata_names) != 1:
            errors.append(
                f"expected exactly one dist-info/METADATA entry, found {metadata_names}"
            )
        else:
            message = BytesParser(policy=email_policy).parsebytes(archive.read(metadata_names[0]))
            package_name = str(message.get("Name") or "")
            version = str(message.get("Version") or "")
            if _canonical_package_name(package_name) != _canonical_package_name(expected_name):
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
        ".dockerignore",
        ".gitignore",
        ".github/workflows/ci.yml",
        "docs/LANGGRAPH_ADAPTER.md",
        "docs/RELEASE_0.29.md",
        "examples/langgraph_adoption.py",
        "pyproject.toml",
        "README.md",
        "schemas/langgraph-binding.schema.json",
        "schemas/langgraph-recovery.schema.json",
        "src/aasm/integrations/langgraph.py",
        "src/aasm/operator_runbooks.py",
        "src/aasm/reference_data/research/manifest.json",
        "src/aasm/runtime_v29.py",
        "tests/test_sdist_smoke.py",
        "tests/test_v29_langgraph_adapter.py",
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


def compare_builds(left_dir: Path, right_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        left = {path.name: path for path in distribution_files(left_dir)}
        right = {path.name: path for path in distribution_files(right_dir)}
    except (FileNotFoundError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)], "files": []}
    if set(left) != set(right):
        errors.append(
            f"build file sets differ: left={sorted(left)} right={sorted(right)}"
        )
    rows: list[dict[str, Any]] = []
    for name in sorted(set(left) & set(right)):
        left_sha = sha256_file(left[name])
        right_sha = sha256_file(right[name])
        left_bytes = left[name].stat().st_size
        right_bytes = right[name].stat().st_size
        identical = left_sha == right_sha and left_bytes == right_bytes
        if not identical:
            errors.append(f"non-reproducible artifact {name}")
        rows.append(
            {
                "name": name,
                "left_sha256": left_sha,
                "right_sha256": right_sha,
                "left_bytes": left_bytes,
                "right_bytes": right_bytes,
                "identical": identical,
            }
        )
    return {"valid": not errors, "files": rows, "errors": errors}


def build_historical_release_report(
    history: dict[str, Any],
    *,
    resolve_tag: Callable[[str], str | None],
    release_commit: str | None = None,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in history.get("releases") or []:
        tag = str(row["tag"])
        expected_commit = str(row["commit"])
        actual_commit = resolve_tag(tag)
        if actual_commit is None:
            status = "PENDING_OWNER_PUBLICATION"
        elif actual_commit == expected_commit:
            status = "VERIFIED"
        else:
            status = "MISMATCH"
            errors.append(
                f"{tag} resolves to {actual_commit}, expected {expected_commit}"
            )
        records.append(
            {
                "tag": tag,
                "title": str(row["title"]),
                "expected_commit": expected_commit,
                "actual_commit": actual_commit,
                "status": status,
            }
        )
    return {
        "schema_version": 1,
        "valid": not errors,
        "release_commit": release_commit,
        "records": records,
        "errors": errors,
    }


