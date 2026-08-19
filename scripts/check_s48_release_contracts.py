from __future__ import annotations

from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(message)


def text(root: Path, path: str) -> str:
    target = root / path
    if not target.exists():
        fail(f"missing S4.8 release-contract file: {path}")
    return target.read_text(encoding="utf-8")


def require(root: Path, path: str, tokens: tuple[str, ...]) -> None:
    source = text(root, path)
    missing = [token for token in tokens if token not in source]
    if missing:
        fail(f"{path} missing S4.8 release-contract tokens: {missing}")


def forbid(root: Path, path: str, tokens: tuple[str, ...]) -> None:
    source = text(root, path)
    present = [token for token in tokens if token in source]
    if present:
        fail(f"{path} leaks pre-admission S4.8 contracts: {present}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model_paths = (
        "src/aasm/safety_envelope_hybrid_state.py",
        "src/aasm/_safety_envelope_common.py",
        "src/aasm/_safety_envelope_records.py",
        "src/aasm/_hybrid_state_records.py",
        "src/aasm/_safety_envelope_assessment_records.py",
        "src/aasm/_safety_envelope_validation.py",
        "src/aasm/_safety_envelope_evaluation.py",
    )
    model = "\n".join(text(root, path) for path in model_paths)
    required_model_tokens = (
        'SAFETY_ENVELOPE_CONTRACT_ID = "aasm.safety.envelope.v1"',
        'HYBRID_STATE_CONTRACT_ID = "aasm.hybrid.state.v1"',
        'SAFETY_ENVELOPE_ASSESSMENT_CONTRACT_ID = "aasm.safety.envelope.assessment.v1"',
        'rule.strength != "HARD_FLOOR"', 'rule.clause.clause_kind != "SAFETY_INVARIANT"',
        '"ode_solver": "NONE"', '"physics_solver": "NONE"',
        '"assessment_is_authorization": False', '"assessment_is_empirical_safety_proof": False',
        '"parallel_safety_state_machine": "NONE"', '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    )
    missing_model_tokens = [token for token in required_model_tokens if token not in model]
    if missing_model_tokens:
        fail(f"S4.8 model sources missing release-contract tokens: {missing_model_tokens}")
    for path in (
        "schemas/safety-envelope.schema.json",
        "schemas/hybrid-state.schema.json",
        "schemas/safety-envelope-assessment.schema.json",
        "tests/test_safety_envelope_hybrid_state_foundation.py",
        "scripts/check_safety_envelope_hybrid_state_contracts.py",
        "docs/implementation/SAFETY_ENVELOPE_HYBRID_STATE_FOUNDATION.md",
    ):
        text(root, path)

    require(root, ".github/workflows/engineering-safety-envelope-hybrid-state.yml", (
        "check_safety_envelope_hybrid_state_contracts.py",
        "tests/test_safety_envelope_hybrid_state_foundation.py",
        "context='aasm/engineering-safety-envelope-hybrid-state'",
    ))
    require(root, ".github/workflows/engineering-s4.yml", (
        "src/aasm/safety_envelope_hybrid_state.py",
        "check_safety_envelope_hybrid_state_contracts.py",
        "tests/test_safety_envelope_hybrid_state_foundation.py",
        "context='aasm/engineering-s4'",
    ))
    require(root, ".github/workflows/v56.yml", (
        "Check S4.8 Safety Envelope and Hybrid State pre-admission foundation",
        "check_safety_envelope_hybrid_state_contracts.py",
        "tests/test_safety_envelope_hybrid_state_foundation.py",
        "check_s48_release_contracts.py",
        "context='aasm/v56'",
    ))
    require(root, ".github/workflows/release.yml", (
        "aasm/engineering-safety-envelope-hybrid-state",
        "python scripts/check_s48_release_contracts.py",
    ))
    forbid(root, "src/aasm/runtime_v56_foundation.py", (
        "from .safety_envelope_hybrid_state", "SafetyEnvelope", "HybridState", "SafetyEnvelopeAssessment",
    ))
    forbid(root, "src/aasm/__init__.py", (
        "from .safety_envelope_hybrid_state import", "SafetyEnvelope", "HybridState", "SafetyEnvelopeAssessment",
    ))

    sys.path.insert(0, str(root / "src"))
    import aasm
    contract = aasm.public_api_contract()
    for key in ("safety_envelope", "hybrid_state", "safety_envelope_assessment"):
        if key in contract:
            fail(f"pre-admission S4.8 surface leaked into active public contract: {key}")
    for name in ("SafetyEnvelope", "HybridState", "SafetyEnvelopeAssessment"):
        if hasattr(aasm, name):
            fail(f"pre-admission S4.8 import leaked into package root: {name}")
    prefixes = ("safety_envelope_", "hybrid_state_")
    if any(name.startswith(prefixes) for name in aasm.SUPPORTED_ENGINE_METHODS):
        fail("pre-admission S4.8 semantic IR leaked into engine method surface")

    print("S4.8 safety-envelope/hybrid-state release and cumulative qualification contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
