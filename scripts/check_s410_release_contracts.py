from __future__ import annotations

from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(message)


def text(root: Path, path: str) -> str:
    target = root / path
    if not target.exists():
        fail(f"missing S4.10 release-contract file: {path}")
    return target.read_text(encoding="utf-8")


def require(root: Path, path: str, tokens: tuple[str, ...]) -> None:
    source = text(root, path)
    missing = [token for token in tokens if token not in source]
    if missing:
        fail(f"{path} missing S4.10 release tokens: {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for path in (
        "fixtures/textpcb/s4-safety-governance-fixtures.json",
        "schemas/textpcb-s4-safety-fixture.schema.json",
        "tests/test_textpcb_s4_safety_governance.py",
        "scripts/check_safety_governance_contracts.py",
        "docs/implementation/TEXTPCB_S4_SAFETY_GOVERNANCE_FIXTURES.md",
    ):
        text(root, path)
    require(
        root,
        ".github/workflows/safety-governance.yml",
        (
            "AASM S4 Aggregate Safety Governance Qualification",
            "tests/test_textpcb_s4_safety_governance.py",
            "context='aasm/safety-governance'",
        ),
    )
    require(
        root,
        ".github/workflows/engineering-s4.yml",
        (
            "check_safety_governance_contracts.py",
            "tests/test_textpcb_s4_safety_governance.py",
            "context='aasm/engineering-s4'",
        ),
    )
    require(
        root,
        ".github/workflows/v56.yml",
        (
            "Check S4.10 TextPCB fixtures and aggregate safety-governance contracts",
            "check_safety_governance_contracts.py",
            "tests/test_textpcb_s4_safety_governance.py",
            "check_s410_release_contracts.py",
            "context='aasm/v56'",
        ),
    )
    require(
        root,
        ".github/workflows/release.yml",
        (
            "aasm/safety-governance",
            "python scripts/check_s410_release_contracts.py",
        ),
    )
    sys.path.insert(0, str(root / "src"))
    import aasm

    contract = aasm.public_api_contract()
    if "textpcb_s4_fixtures" in contract or "safety_governance" in contract:
        fail("qualification-only S4.10 surface leaked into active public contract")
    if any(
        name.startswith(("textpcb_", "safety_governance_"))
        for name in aasm.SUPPORTED_ENGINE_METHODS
    ):
        fail("qualification-only S4.10 surface leaked into engine methods")
    print(
        "S4.10 TextPCB fixture and aggregate safety-governance release contracts: PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
