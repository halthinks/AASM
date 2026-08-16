from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONED_IMPL_RE = re.compile(r"^src/aasm/(?!compat/).*(?:_v|/v)\d+[^/]*\.py$")
FUTURE_VERSION_HEADING_RE = re.compile(r"^##\s+v0\.\d+", re.MULTILINE)
RELEASE_COMMIT_PREFIXES = (
    "Release AASM ",
    "Prepare AASM release ",
)


def run_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_project_version(text: str) -> str:
    data = tomllib.loads(text)
    return str(data["project"]["version"])


def current_project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def valid_base(base: str | None) -> bool:
    if not base or set(base) == {"0"}:
        return False
    try:
        subprocess.check_call(
            ["git", "cat-file", "-e", f"{base}^{{commit}}"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False
    return True


def changed_entries(base: str) -> list[tuple[str, str]]:
    output = run_git("diff", "--name-status", base, "HEAD")
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        entries.append((status, path))
    return entries


def release_change_allowed() -> bool:
    if os.environ.get("AASM_ALLOW_RELEASE_VERSION_CHANGE") == "1":
        return True
    try:
        subject = run_git("log", "-1", "--pretty=%s")
    except Exception:
        return False
    return subject.startswith(RELEASE_COMMIT_PREFIXES)


def check_new_versioned_modules(base: str) -> list[str]:
    violations: list[str] = []
    for status, path in changed_entries(base):
        if not status.startswith(("A", "R", "C")):
            continue
        if VERSIONED_IMPL_RE.match(path):
            violations.append(path)
    return violations


def check_package_version_change(base: str) -> tuple[str, str] | None:
    try:
        old_text = run_git("show", f"{base}:pyproject.toml")
    except subprocess.CalledProcessError:
        return None
    old = read_project_version(old_text)
    new = current_project_version()
    return None if old == new else (old, new)


def check_roadmap() -> list[str]:
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    marker = "## Future capability milestones"
    if marker not in roadmap:
        return ["ROADMAP.md is missing the 'Future capability milestones' policy boundary"]
    future = roadmap.split(marker, 1)[1]
    return [match.group(0) for match in FUTURE_VERSION_HEADING_RE.finditer(future)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce AASM development/release identity policy.")
    parser.add_argument("--base", default=os.environ.get("AASM_VERSION_POLICY_BASE"))
    args = parser.parse_args()

    errors: list[str] = []

    if not (ROOT / "docs" / "VERSIONING.md").exists():
        errors.append("docs/VERSIONING.md is required")

    roadmap_violations = check_roadmap()
    if roadmap_violations:
        errors.extend(f"future roadmap reserves package version: {value}" for value in roadmap_violations)

    if valid_base(args.base):
        new_versioned = check_new_versioned_modules(args.base)
        errors.extend(
            f"new version-numbered implementation module is forbidden: {path}"
            for path in new_versioned
        )

        version_change = check_package_version_change(args.base)
        if version_change and not release_change_allowed():
            old, new = version_change
            errors.append(
                "package version changed during ordinary development "
                f"({old} -> {new}); use an explicit controlled release operation"
            )

    if errors:
        print("AASM version policy: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"AASM version policy: PASS (package target {current_project_version()})")
    if not valid_base(args.base):
        print("No usable base commit supplied; diff-only checks were skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
