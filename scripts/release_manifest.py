from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "venv",
    "__pycache__",
    "htmlcov",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_NAMES = {".DS_Store"}


def iter_files(*, exclude_output: Path | None = None):
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES or path.name in EXCLUDED_NAMES:
            continue
        if path.name.endswith(".db") or path.name.endswith(".db-shm") or path.name.endswith(".db-wal"):
            continue
        if exclude_output is not None and path.resolve() == exclude_output.resolve():
            continue
        yield rel


def file_list_text() -> str:
    return "".join(f"./{rel.as_posix()}\n" for rel in iter_files())


def sha256_text(output: Path) -> str:
    rows=[]
    for rel in iter_files(exclude_output=output):
        digest=hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        rows.append(f"{digest}  {rel.as_posix()}\n")
    return "".join(rows)


def main():
    parser=argparse.ArgumentParser(description="Generate/check AASM release manifests from the actual checkout")
    parser.add_argument("--check-file-list", action="store_true", help="fail if FILE_LIST.txt differs from the checkout")
    parser.add_argument("--write-file-list", action="store_true", help="rewrite FILE_LIST.txt from the checkout")
    parser.add_argument("--sha256", metavar="PATH", help="write a fresh SHA-256 manifest; the output file is excluded from its own hash list")
    args=parser.parse_args()

    expected=file_list_text()
    file_list=ROOT / "FILE_LIST.txt"
    if args.check_file_list:
        actual=file_list.read_text(encoding="utf-8") if file_list.exists() else ""
        if actual != expected:
            raise SystemExit("FILE_LIST.txt is stale; run python scripts/release_manifest.py --write-file-list")
    if args.write_file_list:
        file_list.write_text(expected, encoding="utf-8")
    if args.sha256:
        output=(ROOT / args.sha256).resolve() if not Path(args.sha256).is_absolute() else Path(args.sha256)
        output.write_text(sha256_text(output), encoding="utf-8")

    if not (args.check_file_list or args.write_file_list or args.sha256):
        parser.print_help()


if __name__ == "__main__":
    main()
