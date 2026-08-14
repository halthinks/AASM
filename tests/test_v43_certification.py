import pytest

from aasm.certification import (
    CERTIFICATION_STATUSES,
    CERTIFICATION_TARGET_IDS,
    certification_contract,
    run_certification,
)
from aasm.model import ProblemSpec
from aasm.public_v43 import public_api_contract, validate_public_api_contract
from aasm.runtime_v41 import AASMEngine
from aasm.sii import DynamicWeightController, StructuredProposal, create_sii, sii_contract


def test_certification_contract_is_explicit_and_non_truth-promoting():
    contract = certification_contract()
    assert contract["statuses"] == ["PASS", "FAIL", "INCONCLUSIVE"]
    assert contract["authority"] == "CERTIFICATION_HARNESS_ONLY"
    assert contract["truth_claim"] == "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM"
    assert contract["kernel_changes"] == "NONE"


def test_core_certification_profiles_pass_and_sii_preview_is_inconclusive_by_design():
    report = run_certification()
    assert report["core_status"] == "PASS"
    assert report["status"] == "INCONCLUSIVE"
    assert report["status_counts"]["FAIL"] == 0
    targets = {row["target_id"]: row for row in report["targets"]}
    for target_id in CERTIFICATION_TARGET_IDS[:-1]:
        assert targets[target_id]["status"] == "PASS"
    assert targets["sii-preview"]["status"] == "INCONCLUSIVE"
    inconclusive_ids = {
        check["check_id"]
        for check in targets["sii-preview"]["checks"]
        if check["status"] == "INCONCLUSIVE"
    }
    assert "measurement-principal-authority-binding" in inconclusive_ids
    assert "resource-lease-enforcement" in inconclusive_ids


def test_sii_preview_does_not_change_kernel_or_authority():
    engine = AASMEngine(ProblemSpec("SII preview boundary"))
    sii = create_sii(engine)
    identity = sii.register(principal_id="principal-a", name="reasoner-a")
    proposer_id = identity["identity"]["proposer_id"]
    lease = sii.resource_lease(proposer_id)
    assert lease.authority_class == "PROPOSER"
    assert lease.direct_truth_promotion is False
    assert lease.direct_state_mutation is False
    assert lease.self_verification is False
    assert lease.enforcement == "POLICY_PROJECTION_ONLY_V043"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_sii_proposal_contract_rejects_proposer_controlled_score_fields():
    engine = AASMEngine(ProblemSpec("SII contract"))
    sii = create_sii(engine)
    proposer_id = sii.register(principal_id="principal-b", name="reasoner-b")["identity"]["proposer_id"]
    with pytest.raises(TypeError):
        StructuredProposal(
            proposer_id=proposer_id,
            decision_name="x",
            scope_id="root",
            chosen="a",
            confidence=.5,
            semantic_fingerprint="forged",
        )
    with pytest.raises(TypeError):
        StructuredProposal(
            proposer_id=proposer_id,
            decision_name="x",
            scope_id="root",
            chosen="a",
            confidence=.5,
            reasoning="private chain of thought",
        )


def test_sii_dynamic_weight_controller_uses_measured_reuse_rate():
    controller = DynamicWeightController()
    assert controller.select(phase="normal", measured_reuse_rate=.70).name == "exploitation"
    assert controller.select(phase="normal", measured_reuse_rate=.10).name == "exploration"


def test_sii_contract_exposes_v044_graduation_gates():
    contract = sii_contract()
    assert contract["stability"] == "EXPERIMENTAL_CERTIFICATION_TARGET"
    assert contract["authority_reward"] == "NEVER"
    assert contract["kernel_runtime"] == "V0.41_ENGINE_UNCHANGED"
    assert "measurement_principal_authority_binding" in contract["v044_graduation_gates"]
    assert "resource_lease_scheduler_enforcement" in contract["v044_graduation_gates"]


def test_v43_public_contract_is_live():
    contract = public_api_contract()
    assert contract["runtime_version"] == "0.43.0"
    assert contract["contract_version"] == "0.19.0"
    assert contract["certification"]["contract_id"] == "aasm.certification.v1"
    assert contract["sii_preview"]["contract_id"] == "aasm.sii.v1"
    result = validate_public_api_contract()
    assert result["valid"], result["errors"]


def test_v43_cli_commands_are_declared():
    contract = public_api_contract()
    for command in ("certification-contract", "certify", "sii-contract"):
        assert command in contract["supported_cli_commands"]
    assert set(CERTIFICATION_STATUSES) == {"PASS", "FAIL", "INCONCLUSIVE"}
