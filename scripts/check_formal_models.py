from __future__ import annotations

from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing required formal-contract tokens {missing}")


def forbid(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden obsolete formal-contract tokens {present}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tla = root / "formal" / "AASMCalculus.tla"
    cfg = root / "formal" / "AASMCalculus.cfg"
    promela = root / "formal" / "aasm_calculus.pml"

    require(
        tla,
        [
            "StageCandidate",
            "ActivateCandidate",
            "LearnSoft",
            "RegisterCertificate",
            "VerifyCertificate",
            "PromoteHard",
            "HardRequiresCertificate",
            "VerifiedRequiresRegistration",
            "HardComesFromSoft",
            "CandidateActivationIsAtomic",
            "FairnessProgress",
            "Restart",
            "TerminalStutter",
        ],
    )
    forbid(tla, ["LearnCertified =="])
    require(
        cfg,
        [
            "SPECIFICATION Spec",
            "HardRequiresCertificate",
            "VerifiedRequiresRegistration",
            "CandidateActivationIsAtomic",
            "FairnessProgress",
        ],
    )
    require(
        promela,
        [
            "soft_knowledge",
            "registered_certificate",
            "verified_certificate",
            "hard_knowledge",
            "HARD_REQUIRES_CERT",
            "VERIFIED_REQUIRES_REGISTRATION",
            "CANDIDATE_ATOMIC",
            "MAX_FAIRNESS_DEBT",
            "fairness_progress",
            "RESTART",
        ],
    )

    require(
        root / "src" / "aasm" / "runtime_v24.py",
        [
            "def _commit_calculus",
            "def learn_constraint",
            "effective_strength = \"SOFT\"",
            "assert_hard_constraint_certification",
            "def promote_constraint_hard",
        ],
    )
    require(
        root / "src" / "aasm" / "runtime_v23.py",
        [
            "def _stage_candidate_activation",
            "def _validate_calculus_state_for_commit",
            "\"calculus\": staged_calculus",
            "\"candidate_state\": state",
        ],
    )
    require(
        root / "src" / "aasm" / "assurance.py",
        [
            "NON_CONTIGUOUS_SEQUENCE",
            "PERSISTED_SNAPSHOT_MISMATCH",
            "assert_calculus_invariants",
            "hard_constraint_certification_issues",
        ],
    )
    require(
        root / "src" / "aasm" / "observability.py",
        ["def causal_graph", "def _closed_graph", "EXPOSE_OR_DISPOSITION"],
    )

    print("formal and runtime assurance source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
