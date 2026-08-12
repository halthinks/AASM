from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

from release_artifacts_core import (
    GitHubReleaseError,
    build_historical_release_report,
    release_assets,
    sha256_file,
    verify_release_history,
)

def _run_gh_json(endpoint: str, *, missing_ok: bool = False) -> dict[str, Any] | None:
    completed = subprocess.run(
        ["gh", "api", endpoint],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        diagnostic = (completed.stderr + "\n" + completed.stdout).strip()
        lowered = diagnostic.lower()
        if missing_ok and ("404" in lowered or "not found" in lowered):
            return None
        raise GitHubReleaseError(f"gh api {endpoint!r} failed: {diagnostic}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise GitHubReleaseError(
            f"gh api {endpoint!r} returned invalid JSON"
        ) from exc


def resolve_github_tag(repository: str, tag: str) -> str | None:
    ref = _run_gh_json(f"repos/{repository}/git/ref/tags/{tag}", missing_ok=True)
    if ref is None:
        return None
    obj = dict(ref.get("object") or {})
    for _ in range(8):
        object_type = str(obj.get("type") or "")
        sha = str(obj.get("sha") or "")
        if object_type == "commit":
            return sha
        if object_type != "tag" or not sha:
            raise GitHubReleaseError(
                f"tag {tag!r} has unsupported object {object_type!r} {sha!r}"
            )
        annotated = _run_gh_json(f"repos/{repository}/git/tags/{sha}")
        assert annotated is not None
        obj = dict(annotated.get("object") or {})
    raise GitHubReleaseError(f"tag {tag!r} exceeded the tag-resolution depth limit")


def write_historical_release_report(
    history_path: Path,
    *,
    repository: str,
    output_path: Path,
    release_commit: str | None = None,
) -> dict[str, Any]:
    history_report = verify_release_history(history_path)
    if not history_report["valid"]:
        return history_report
    report = build_historical_release_report(
        history_report,
        resolve_tag=lambda tag: resolve_github_tag(repository, tag),
        release_commit=release_commit,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def verify_release_asset_snapshot(
    dist_dir: Path,
    *,
    release: dict[str, Any],
    resolved_tag_commit: str | None,
    expected_tag: str,
    expected_commit: str,
) -> dict[str, Any]:
    errors: list[str] = []
    local = {path.name: path for path in release_assets(dist_dir)}
    remote_rows = list(release.get("assets") or [])
    remote = {str(row.get("name") or ""): row for row in remote_rows}
    if str(release.get("tag_name") or "") != expected_tag:
        errors.append(
            f"release tag {release.get('tag_name')!r} does not match {expected_tag!r}"
        )
    if resolved_tag_commit != expected_commit:
        errors.append(
            f"release tag resolves to {resolved_tag_commit!r}, expected {expected_commit!r}"
        )
    if bool(release.get("draft")):
        errors.append("release is still a draft")
    if set(local) != set(remote):
        errors.append(
            f"release asset sets differ: local={sorted(local)} remote={sorted(remote)}"
        )
    rows: list[dict[str, Any]] = []
    for name in sorted(set(local) & set(remote)):
        local_sha = sha256_file(local[name])
        expected_digest = f"sha256:{local_sha}"
        remote_digest = str(remote[name].get("digest") or "")
        local_bytes = local[name].stat().st_size
        remote_bytes = int(remote[name].get("size") or -1)
        valid = remote_digest == expected_digest and remote_bytes == local_bytes
        if remote_digest != expected_digest:
            errors.append(
                f"asset {name} digest {remote_digest!r} does not match {expected_digest!r}"
            )
        if remote_bytes != local_bytes:
            errors.append(
                f"asset {name} size {remote_bytes} does not match {local_bytes}"
            )
        rows.append(
            {
                "name": name,
                "sha256": local_sha,
                "bytes": local_bytes,
                "remote_digest": remote_digest,
                "remote_bytes": remote_bytes,
                "valid": valid,
            }
        )
    return {
        "valid": not errors,
        "tag": expected_tag,
        "commit_sha": expected_commit,
        "assets": rows,
        "errors": errors,
    }


def verify_github_release(
    tag: str,
    dist_dir: Path,
    *,
    repository: str,
    expected_commit: str,
) -> dict[str, Any]:
    release = _run_gh_json(f"repos/{repository}/releases/tags/{tag}")
    assert release is not None
    resolved = resolve_github_tag(repository, tag)
    return verify_release_asset_snapshot(
        dist_dir,
        release=release,
        resolved_tag_commit=resolved,
        expected_tag=tag,
        expected_commit=expected_commit,
    )


