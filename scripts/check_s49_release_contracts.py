from __future__ import annotations

from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(message)


def text(root: Path, path: str) -> str:
    target = root / path
    if not target.exists():
        fail(f"missing S4.9 release-contract file: {path}")
    return target.read_text(encoding="utf-8")


def require(root: Path, path: str, tokens: tuple[str, ...]) -> None:
    source = text(root, path)
    missing = [token for token in tokens if token not in source]
    if missing:
        fail(f"{path} missing S4.9 release-contract tokens: {missing}")


def forbid(root: Path, path: str, tokens: tuple[str, ...]) -> None:
    source = text(root, path)
    present = [token for token in tokens if token in source]
    if present:
        fail(f"{path} leaks pre-admission S4.9 contracts: {present}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model = "\n".join(
        text(root, path)
        for path in (
            "src/aasm/epistemic_debt_manual_override.py",
            "src/aasm/_epistemic_debt.py",
            "src/aasm/_manual_override.py",
        )
    )
    tokens = (
        'EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"',
        'MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"',
        'MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"',
        '"debt_graph": "NONE_SECONDARY_OR_PARALLEL"',
        '"hard_floor_override": "FORBIDDEN_UNCONDITIONALLY"',
        '"assessment_is_authorization": False',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    )
    missing = [token for token in tokens if token not in model]
    if missing:
        fail(f"S4.9 model missing release-contract tokens: {missing}")
    for path in (
        "schemas/epistemic-debt.schema.json",
        "schemas/manual-override.schema.json",
        "schemas/manual-override-assessment.schema.json",
        "tests/test_epistemic_debt_manual_override_foundation.py",
        "scripts/check_epistemic_debt_manual_override_contracts.py",
        "docs/implementation/EPISTEMIC_DEBT_MANUAL_OVERRIDE_FOUNDATION.md",
    ):
        text(root, path)
    require(
        root,
        ".github/workflows/engineering-epistemic-debt-manual-override.yml",
        (
            "check_epistemic_debt_manual_override_contracts.py",
            "tests/test_epistemic_debt_manual_override_foundation.py",
            "context='aasm/engineering-epistemic-debt-manual-override'",
        ),
    )
    require(
        root,
        ".github/workflows/engineering-s4.yml",
        (
            "src/aasm/epistemic_debt_manual_override.py",
            "check_epistemic_debt_manual_override_contracts.py",
            "tests/test_epistemic_debt_manual_override_foundation.py",
            "context='aasm/engineering-s4'",
        ),
    )
    require(
        root,
        ".github/workflows/v56.yml",
        (
            "Check S4.9 Epistemic Debt and Manual Override pre-admission foundation",
            "check_epistemic_debt_manual_override_contracts.py",
            "tests/test_epistemic_debt_manual_override_foundation.py",
            "check_s49_release_contracts.py",
            "context='aasm/v56'",
        ),
    )
    require(
        root,
        ".github/workflows/release.yml",
        (
            "aasm/engineering-epistemic-debt-manual-override",
            "python scripts/check_s49_release_contracts.py",
        ),
    )
    forbid(
        root,
        "src/aasm/runtime_v56_foundation.py",
        (
            "from .epistemic_debt_manual_override",
            "EpistemicDebtProjection",
            "ManualOverride",
            "ManualOverrideAssessment",
        ),
    )
    forbid(
        root,
        "src/aasm/__init__.py",
        (
            "from .epistemic_debt_manual_override import",
            "EpistemicDebtProjection",
            "ManualOverride",
            "ManualOverrideAssessment",
        ),
    )
    sys.path.insert(0, str(root / "src"))
    import aasm

    contract = aasm.public_api_contract()
    for key in (
        "epistemic_debt",
        "manual_override",
        "manual_override_assessment",
    ):
        if key in contract:
            fail(f"pre-admission S4.9 surface leaked into active contract: {key}")
    for name in (
        "EpistemicDebtProjection",
        "ManualOverride",
        "ManualOverrideAssessment",
    ):
        if hasattr(aasm, name):
            fail(f"pre-admission S4.9 import leaked into package root: {name}")
    prefixes = ("epistemic_debt_", "manual_override_")
    if any(name.startswith(prefixes) for name in aasm.SUPPORTED_ENGINE_METHODS):
        fail("pre-admission S4.9 semantic IR leaked into engine methods")
    print("S4.9 epistemic-debt/manual-override release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
