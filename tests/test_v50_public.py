from aasm import public_v49 as v49
from aasm.cli_v50 import build_parser
from aasm.public_v50 import (
    AASMEngine,
    PUBLIC_RELEASE_STABILITY,
    SOLVER_PROOF_CONTRACT_ID,
    SOLVER_PROOF_CONTRACT_VERSION,
    SolverClaim,
    SolverClaimCertificate,
    SolverProofArtifact,
    __version__,
    public_api_contract,
    run_solver_proof_conformance,
    validate_public_api_contract,
)
from aasm.runtime_v49 import AASMEngine as V49Engine
from aasm.runtime_v50 import AASMEngine as V50Engine


def test_v50_public_contract_is_composed_over_v49():
    assert __version__ == "0.50.0"
    assert AASMEngine is V50Engine
    assert issubclass(V50Engine, V49Engine)
    report = validate_public_api_contract()
    assert report["valid"], report["errors"]
    contract = report["contract"]
    assert contract["contract_version"] == "0.26.0"
    assert contract["runtime_version"] == "0.50.0"
    assert contract["release_stability"] == "ACTIVE_DEVELOPMENT"
    assert contract["solver_proof_claims"]["contract_id"] == SOLVER_PROOF_CONTRACT_ID
    assert contract["solver_proof_claims"]["contract_version"] == SOLVER_PROOF_CONTRACT_VERSION
    assert contract["solver_proof_claims"]["certificate_authority"] == "EVIDENCE_ONLY"
    assert contract["solver_proof_claims"]["truth_authority"] == "EXISTING_AASM_POLICY_ONLY"


def test_v50_does_not_mutate_v49_public_contract():
    assert v49.__version__ == "0.49.0"
    assert v49.public_api_contract()["contract_version"] == "0.25.0"
    assert "solver_proof_claims" not in v49.public_api_contract()


def test_v50_public_types_are_exported():
    assert SolverClaim.__name__ == "SolverClaim"
    assert SolverProofArtifact.__name__ == "SolverProofArtifact"
    assert SolverClaimCertificate.__name__ == "SolverClaimCertificate"
    assert PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"


def test_v50_cli_commands_are_visible():
    help_text = build_parser().format_help()
    assert "solver-proof-contract" in help_text
    assert "solver-proof-conformance" in help_text
    contract = public_api_contract()
    assert "solver-proof-contract" in contract["supported_cli_commands"]
    assert "solver-proof-conformance" in contract["supported_cli_commands"]


def test_v50_conformance_is_public_and_passes():
    report = run_solver_proof_conformance()
    assert report["status"] == "PASS", report
