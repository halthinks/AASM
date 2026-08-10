from __future__ import annotations

from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing required formal-contract tokens {missing}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    require(
        root / "formal" / "AASMCalculus.tla",
        [
            "HardRequiresCertificate",
            "CompleteIsSafe",
            "ResolvedNotOpen",
            "Restart",
            "TerminalStutter",
        ],
    )
    require(
        root / "formal" / "AASMCalculus.cfg",
        ["SPECIFICATION Spec", "HardRequiresCertificate", "CompleteIsSafe"],
    )
    require(
        root / "formal" / "aasm_calculus.pml",
        ["HARD_REQUIRES_CERT", "COMPLETE_SAFE", "RESOLVED_NOT_OPEN", "RESTART"],
    )
    print("formal model source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
