from __future__ import annotations
from pathlib import Path
import tomllib

def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8"); missing = [t for t in tokens if t not in text]
    if missing: raise SystemExit(f"{path}: missing release/readiness tokens {missing}")

def forbid(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8"); present = [t for t in tokens if t in text]
    if present: raise SystemExit(f"{path}: forbidden tokens {present}")

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle: version = str(tomllib.load(handle)["project"]["version"])
    if version != "0.33.0": raise SystemExit(f"unexpected release version: {version}")
    require(root / "src/aasm/__init__.py", ['__version__ = "0.33.0"', '"contract_version": "0.9.0"', 'PROVENANCE_CONTRACT_ID'])
    require(root / "src/aasm/trace_conformance.py", ['PROVENANCE_CONTRACT_ID = "aasm.provenance.v1"', 'def export_provenance', 'def verify_provenance_export', 'def create_selective_provenance_export', 'HMAC-SHA256'])
    require(root / "src/aasm/cli_v32.py", ["provenance-export", "provenance-verify", "provenance-select"])
    require(root / "README.md", ["Current release — v0.33.0", "Signed Provenance and Verifiable Exports", "v0.34.0 — Distributed Recovery Certification"])
    require(root / "ROADMAP.md", ["v0.33.0 — Signed Provenance and Verifiable Exports", "Current — implemented", "v0.36.0 — Semantic Compiler SDK"])
    require(root / "docs/CURRENT_RELEASE.md", ["AASM v0.33.0", "aasm.provenance.v1 / 0.1.0"])
    release = root / ".github/workflows/release.yml"
    require(release, ['workflows: ["CI"]', "aasm/ci-summary", "aasm/formal-assurance", 'gh release create "$TAG"', '--notes-file docs/CURRENT_RELEASE.md', "verify-github-release"])
    forbid(release, ["--clobber", "git tag -a"])
    print("v0.33 provenance, documentation, and release contracts: PASS"); return 0

if __name__ == "__main__": raise SystemExit(main())
