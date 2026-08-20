from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aasm.refinement import (
    RefinementApplicability,
    RefinementProposal,
    RefinementSemanticEffect,
    RefinementValidation,
    validate_refinement_validation,
)
from aasm.textpcb_refinement import (
    TEXTPCB_EVALUATOR_DOMAINS,
    TEXTPCB_REFINEMENT_AUTHORITY_CEILING,
    TEXTPCB_REFINEMENT_GATE,
    TEXTPCB_REQUIRED_REFINEMENT_GATE,
    TEXTPCB_REQUIRED_SAFETY_GATE,
    TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT,
    TextPCBEvaluatorResult,
    textpcb_refinement_contract,
    validate_textpcb_evaluator_result,
)


BASE_FP = "a" * 64
TARGET_FP = "b" * 64
PROJECTION_FP = "c" * 64


def _proposal(
    kind: str,
    *,
    evaluator: str = "textpcb-evaluator",
    base_fingerprint: str = BASE_FP,
    evidence_ids: tuple[str, ...] = ("ev-tool-result",),
) -> RefinementProposal:
    return RefinementProposal(
        refinement_kind=kind,
        workspace_id="workspace-1",
        scope_id="board-1",
        base_revision_id="problem-revision-1",
        base_revision_fingerprint=base_fingerprint,
        producer_principal_id=evaluator,
        trigger_evidence_ids=evidence_ids,
        applicability=RefinementApplicability(
            workspace_id="workspace-1",
            scope_id="board-1",
            problem_revision_id="problem-revision-1",
            problem_revision_fingerprint=base_fingerprint,
            subject_ids=("pcb-main",),
        ),
        expected_semantic_effect=RefinementSemanticEffect(
            target_problem_fingerprint=TARGET_FP,
            target_semantic_projection_fingerprint=PROJECTION_FP,
            changed_semantic_ids=("pcb-main",),
        ),
        proposed_semantic_payload={"domain_action": kind},
    )


def _result(
    domain: str,
    result: str,
    proposal_kind: str | None,
    *,
    evidence_ids: tuple[str, ...] = ("ev-tool-result",),
    artifact_ids: tuple[str, ...] = (),
) -> TextPCBEvaluatorResult:
    proposal = None if proposal_kind is None else _proposal(proposal_kind, evidence_ids=evidence_ids)
    return TextPCBEvaluatorResult(
        evaluator_id="textpcb-evaluator",
        domain=domain,
        workspace_id="workspace-1",
        scope_id="board-1",
        base_revision_id="problem-revision-1",
        base_revision_fingerprint=BASE_FP,
        result=result,
        evidence_ids=evidence_ids,
        counterexamples=({"subject": "pcb-main", "finding": "violated"},) if result == "FAIL" else (),
        diagnoses=("typed evaluator diagnosis",) if result != "PASS" else (),
        artifact_ids=artifact_ids,
        proposal=proposal,
    )


def _load_fixture() -> dict:
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "fixtures" / "textpcb" / "s5-refinement-qualification-fixtures.json").read_text())


def test_all_required_textpcb_domains_are_permanently_covered() -> None:
    fixture = _load_fixture()
    fixture_domains = {case["domain"] for case in fixture["cases"]}
    assert fixture_domains == set(TEXTPCB_EVALUATOR_DOMAINS)
    assert fixture["qualification_gate"] == TEXTPCB_REFINEMENT_GATE
    assert fixture["required_refinement_gate"] == TEXTPCB_REQUIRED_REFINEMENT_GATE
    assert fixture["required_safety_gate"] == TEXTPCB_REQUIRED_SAFETY_GATE


def test_fixture_suite_fingerprint_is_canonical_and_reuses_s4_safety_corpus() -> None:
    fixture = _load_fixture()
    supplied = fixture.pop("suite_fingerprint")
    canonical = json.dumps(fixture, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == supplied
    root = Path(__file__).resolve().parents[1]
    s4 = json.loads((root / "fixtures" / "textpcb" / "s4-safety-governance-fixtures.json").read_text())
    assert s4["suite_fingerprint"] == TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT
    assert fixture["required_s4_safety_suite_fingerprint"] == s4["suite_fingerprint"]


@pytest.mark.parametrize(
    ("domain", "result", "proposal_kind"),
    [
        ("DRC_ERC", "FAIL", "NEW_CONSTRAINT"),
        ("SPICE", "FAIL", "MODEL_CORRECTION"),
        ("EM", "FAIL", "BOUND_TIGHTENING"),
        ("THERMAL_PDN", "INCONCLUSIVE", "VERIFICATION_ESCALATION"),
        ("MECHANICAL_MANUFACTURING", "FAIL", "DOMAIN_RESTRICTION"),
        ("EXTERNAL_MEASUREMENT", "INCONCLUSIVE", "REQUIRED_OBSERVATION"),
        ("ARTIFACT_TOOL_FEEDBACK", "FAIL", "VERIFICATION_ESCALATION"),
    ],
)
def test_every_engineering_feedback_domain_emits_only_generic_refinement_proposals(
    domain: str, result: str, proposal_kind: str
) -> None:
    item = _result(domain, result, proposal_kind)
    report = validate_textpcb_evaluator_result(item)
    assert report["valid"] is True
    assert report["authority"] == "NONE"
    assert report["artifact_acceptance"] == "NONE"
    assert report["proposal"]["refinement_kind"] == proposal_kind
    assert report["proposal"]["contract_id"] == "aasm.refinement.proposal.v1"
    assert report["proposal"]["trigger_evidence_ids"] == ["ev-tool-result"]
    assert "problem.refinement.apply" in report["canonical_application_path"]


def test_result_round_trip_is_deterministic() -> None:
    item = _result("SPICE", "FAIL", "MODEL_CORRECTION")
    restored = TextPCBEvaluatorResult.from_dict(item.to_dict())
    assert restored.to_dict() == item.to_dict()
    assert restored.fingerprint == item.fingerprint


def test_pass_is_evidence_not_artifact_acceptance_and_cannot_smuggle_proposal() -> None:
    passed = _result("ARTIFACT_TOOL_FEEDBACK", "PASS", None, artifact_ids=("artifact-revision-17",))
    payload = passed.to_dict()
    assert payload["artifact_ids"] == ["artifact-revision-17"]
    assert payload["artifact_acceptance_claim"] == "NONE"
    assert payload["authority_claim"] == "NONE"
    with pytest.raises(ValueError, match="PASS result cannot smuggle"):
        _result("ARTIFACT_TOOL_FEEDBACK", "PASS", "VERIFICATION_ESCALATION")


def test_evaluator_and_proposal_revision_binding_fails_closed() -> None:
    proposal = _proposal("NEW_CONSTRAINT")
    with pytest.raises(ValueError, match="base revision fingerprint"):
        TextPCBEvaluatorResult(
            evaluator_id="textpcb-evaluator",
            domain="DRC_ERC",
            workspace_id="workspace-1",
            scope_id="board-1",
            base_revision_id="problem-revision-1",
            base_revision_fingerprint="d" * 64,
            result="FAIL",
            evidence_ids=("ev-tool-result",),
            diagnoses=("stale result",),
            proposal=proposal,
        )


def test_evaluator_evidence_cannot_be_dropped_from_proposal_lineage() -> None:
    proposal = _proposal("NEW_CONSTRAINT", evidence_ids=("different-evidence",))
    with pytest.raises(ValueError, match="must be retained"):
        TextPCBEvaluatorResult(
            evaluator_id="textpcb-evaluator",
            domain="DRC_ERC",
            workspace_id="workspace-1",
            scope_id="board-1",
            base_revision_id="problem-revision-1",
            base_revision_fingerprint=BASE_FP,
            result="FAIL",
            evidence_ids=("ev-tool-result",),
            diagnoses=("trace clearance",),
            proposal=proposal,
        )


def test_inconclusive_cannot_be_laundered_into_semantic_correction() -> None:
    with pytest.raises(ValueError, match="may only request observation or verification escalation"):
        _result("THERMAL_PDN", "INCONCLUSIVE", "MODEL_CORRECTION")


def test_generic_s51_independent_validator_rule_applies_to_textpcb_producer() -> None:
    proposal = _proposal("MODEL_CORRECTION")
    validation = RefinementValidation(
        proposal_id=proposal.proposal_id,
        proposal_fingerprint=proposal.fingerprint,
        semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
        base_revision_id=proposal.base_revision_id,
        base_revision_fingerprint=proposal.base_revision_fingerprint,
        applicability_fingerprint=proposal.applicability.fingerprint,
        validator_principal_id=proposal.producer_principal_id,
        result="VALID",
        supporting_evidence_ids=("ev-independent-check",),
        reasoning="attempted self-validation",
    )
    report = validate_refinement_validation(proposal, validation)
    assert report["application_eligible"] is False
    assert "INDEPENDENT_VALIDATOR_REQUIRED" in report["errors"]


def test_textpcb_layer_has_no_authority_or_runtime_surface() -> None:
    contract = textpcb_refinement_contract()
    assert contract["generic_refinement_contract_id"] == "aasm.refinement.loop.v1"
    assert contract["required_refinement_gate"] == "aasm/refinement"
    assert contract["required_safety_gate"] == "aasm/safety-governance"
    assert contract["authority_ceiling"] == TEXTPCB_REFINEMENT_AUTHORITY_CEILING
    assert contract["authority_ceiling"]["evaluator_direct_problem_mutation"] == "FORBIDDEN"
    assert contract["authority_ceiling"]["evaluator_direct_artifact_acceptance"] == "FORBIDDEN"
    assert contract["authority_ceiling"]["runtime_admission"] == "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE"


def test_fixture_adversarial_requirements_remain_explicit() -> None:
    fixture = _load_fixture()
    by_id = {case["fixture_id"]: case for case in fixture["cases"]}
    assert by_id["stale-revision-fails-closed"]["expected"] == "FAIL_CLOSED_REVISION_MISMATCH"
    assert by_id["producer-cannot-self-apply"]["expected"] == "GENERIC_REFINEMENT_AUTHORITY_PATH_REQUIRED"
    assert by_id["safety-floor-survives-refinement"]["expected"] == "S4_SAFETY_GOVERNANCE_REMAINS_AUTHORITATIVE"
    assert "resource exhaustion weakens legality" in by_id["safety-floor-survives-refinement"]["forbidden_claims"]
