from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def _safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in archive.getmembers():
        target = (destination / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise AssertionError(f"unsafe source-distribution member: {member.name}")
    archive.extractall(destination)


def test_source_distribution_is_self_contained(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    archives = sorted(dist.glob("*.tar.gz"))
    assert len(archives) == 1, archives

    extracted = tmp_path / "extracted"
    extracted.mkdir()
    with tarfile.open(archives[0], "r:gz") as archive:
        _safe_extract(archive, extracted)

    roots = [path for path in extracted.iterdir() if path.is_dir()]
    assert len(roots) == 1, roots
    env = dict(os.environ)
    env["PYTHONPATH"] = str(roots[0] / "src")
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/test_sdist_smoke.py"],
        cwd=roots[0],
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
