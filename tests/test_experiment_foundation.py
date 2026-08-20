from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import validate

from aasm.experiment import (
    EXPERIMENT_CONTRACT_ID,
    ExperimentContextBinding,
    ExperimentHypothesis,
    ExperimentOutcomeCriterion,
    ExperimentProcedureStep,
    ExperimentSelectionCandidate,
    ExperimentSelectionProposal,
    ExperimentSpec,
    ExperimentVariable,
    experiment_contract,
    propose_experiment_selection,
)
from aasm.semantic_dependencies import SemanticNodeRef
from aasm.semantic_result import semantic_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _bound(kind: str, label: str, contract: str, *, evidence=("evidence-context",)) -> ExperimentContextBinding:
    return ExperimentContextBinding(
        kind,
        "BOUND",
        contract_id=contract,
        object_id=f"{kind.lower()}-{label}",
        object_fingerprint=_sha(f"{kind}-{label}"),
        evidence_ids=tuple(evidence),
    )


def _spec(name: str = "clearance discrimination") -> ExperimentSpec:
    hypothesis_a = ExperimentHypothesis(
        "clearance failure is caused by geometry",
        semantic_refs=(SemanticNodeRef("CONSTRAINT", "clearance-rule"),),
        basis_evidence_ids=("evidence-drc",),
    )
    hypothesis_b = ExperimentHypothesis(
        "clearance failure is caused by stale manufacturing assumptions",
        semantic_refs=(SemanticNodeRef("RULE", "manufacturing-rule"),),
        basis_evidence_ids=("evidence-drc",),
    )
    return ExperimentSpec(
        experiment_name=name,
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("problem-r1"),
        hypotheses=(hypothesis_a, hypothesis_b),
        variables=(
            ExperimentVariable("clearance-setting", "CONTROLLED", SemanticNodeRef("CONSTRAINT", "clearance-setting"), _sha("controlled-clearance")),
            ExperimentVariable("drc-violations", "MEASURED", SemanticNodeRef("EVIDENCE", "drc-count"), _sha("measured-drc")),
        ),
        procedure_steps=(
            ExperimentProcedureStep("prepare", 0, "prepare the candidate under the exact bound revision", required_capability_ids=("cad.generate",)),
            ExperimentProcedureStep("verify", 1, "run the declared verifier and record observations", required_capability_ids=("drc.verify",)),
        ),
        context_bindings=(
            _bound("ENVIRONMENT", "sim", "aasm.execution.environment-binding.v1"),
            ExperimentContextBinding("FIXTURE_IDENTITY", "NOT_APPLICABLE", reason="simulation-only experiment has no physical fixture"),
            ExperimentContextBinding("CALIBRATION_IDENTITY", "NOT_APPLICABLE", reason="simulation-only verifier has no physical calibration artifact"),
            _bound("EVIDENCE_FLOOR", "policy", "aasm.evidence.policy.v1"),
            _bound("RISK_CONSTRAINT", "risk", "aasm.risk.assessment.v1"),
            _bound("RESOURCE_DEMAND", "demand", "aasm.resource.demand.v1"),
            _bound("VERIFICATION_OBLIGATION", "verify", "aasm.obligation.phase.v1"),
        ),
        outcome_criteria=(
            ExperimentOutcomeCriterion(
                "geometry-supported",
                "violations change with controlled geometry while manufacturing assumption is fixed",
                _sha("predicate-geometry"),
                supports_hypothesis_ids=(hypothesis_a.hypothesis_id,),
                contradicts_hypothesis_ids=(hypothesis_b.hypothesis_id,),
            ),
            ExperimentOutcomeCriterion(
                "assumption-supported",
                "violations persist under geometry sweep and change only with manufacturing assumption",
                _sha("predicate-assumption"),
                supports_hypothesis_ids=(hypothesis_b.hypothesis_id,),
                contradicts_hypothesis_ids=(hypothesis_a.hypothesis_id,),
            ),
            ExperimentOutcomeCriterion(
                "inconclusive",
                "observations do not discriminate the hypotheses",
                _sha("predicate-inconclusive"),
                inconclusive=True,
            ),
        ),
        producer_principal_id="planner-a",
        evidence_ids=("evidence-diagnosis",),
    )


def test_experiment_contract_is_pre_admission_and_has_no_execution_or_authority_plane():
    contract = experiment_contract()
    assert contract["contract_id"] == EXPERIMENT_CONTRACT_ID
    assert contract["selection_is_proposal_only"] is True
    assert contract["experiment_execution"] == "NONE"
    assert contract["effect_dispatch"] == "NONE"
    assert contract["resource_reservation"] == "NONE"
    assert contract["fact_authority"] == "NONE"
    assert contract["effect_authority"] == "NONE"
    assert contract["problem_mutation"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_experiment_round_trip_and_schemas_are_exact():
    spec = _spec()
    clone = ExperimentSpec.from_dict(spec.to_dict())
    assert clone.fingerprint == spec.fingerprint
    assert clone.to_dict() == spec.to_dict()
    schema = json.loads((ROOT / "schemas" / "experiment.schema.json").read_text(encoding="utf-8"))
    validate(spec.to_dict(), schema)

    candidate = ExperimentSelectionCandidate(
        spec.experiment_id,
        spec.fingerprint,
        spec.problem_revision_id,
        spec.problem_revision_fingerprint,
        "ELIGIBLE",
        ("evidence-hard-gates",),
        700000,
        500000,
    )
    proposal = propose_experiment_selection(
        workspace_id=spec.workspace_id,
        scope_id=spec.scope_id,
        problem_revision_id=spec.problem_revision_id,
        problem_revision_fingerprint=spec.problem_revision_fingerprint,
        candidates=(candidate,),
        selection_policy_id="policy-info-gain-v1",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=("evidence-selection-basis",),
    )
    selection_schema = json.loads((ROOT / "schemas" / "experiment-selection-proposal.schema.json").read_text(encoding="utf-8"))
    validate(proposal.to_dict(), selection_schema)
    assert ExperimentSelectionProposal.from_dict(proposal.to_dict()).fingerprint == proposal.fingerprint


def test_binary_float_is_forbidden_in_portable_experiment_identity():
    spec = _spec()
    payload = spec.to_dict()
    payload.pop("fingerprint")
    payload.pop("experiment_id")
    payload["metadata"] = {"unsafe_binary_float": 0.25}
    with pytest.raises(TypeError, match="binary floating-point"):
        ExperimentSpec.from_dict(payload)


def test_fixture_and_calibration_must_be_bound_or_explicitly_not_applicable():
    spec = _spec()
    payload = spec.to_dict()
    payload.pop("fingerprint")
    payload.pop("experiment_id")
    payload["context_bindings"] = [
        row for row in payload["context_bindings"]
        if row["binding_kind"] not in {"FIXTURE_IDENTITY", "CALIBRATION_IDENTITY"}
    ]
    with pytest.raises(ValueError, match="fixture identity"):
        ExperimentSpec.from_dict(payload)

    with pytest.raises(ValueError, match="cannot be NOT_APPLICABLE"):
        ExperimentContextBinding("RESOURCE_DEMAND", "NOT_APPLICABLE", reason="resource unknown")


def test_hard_context_references_cannot_be_silently_omitted():
    spec = _spec()
    for kind, message in (
        ("ENVIRONMENT", "execution environment"),
        ("EVIDENCE_FLOOR", "evidence-floor"),
        ("RESOURCE_DEMAND", "resource-demand"),
        ("RISK_CONSTRAINT", "safety/risk"),
    ):
        payload = spec.to_dict()
        payload.pop("fingerprint")
        payload.pop("experiment_id")
        payload["context_bindings"] = [row for row in payload["context_bindings"] if row["binding_kind"] != kind]
        with pytest.raises(ValueError, match=message):
            ExperimentSpec.from_dict(payload)


def test_controlled_and_measured_semantic_variables_must_be_disjoint():
    spec = _spec()
    payload = spec.to_dict()
    payload.pop("fingerprint")
    payload.pop("experiment_id")
    payload["variables"][1]["semantic_ref"] = deepcopy(payload["variables"][0]["semantic_ref"])
    payload["variables"][1].pop("fingerprint")
    with pytest.raises(ValueError, match="must be disjoint"):
        ExperimentSpec.from_dict(payload)


def test_selection_never_lets_information_gain_override_hard_constraint_gate():
    eligible = ExperimentSelectionCandidate(
        "experiment-" + "1" * 24,
        _sha("eligible-experiment"),
        "problem-revision-r1",
        _sha("problem-r1"),
        "ELIGIBLE",
        ("evidence-eligible-gates",),
        400000,
        300000,
    )
    unsafe = ExperimentSelectionCandidate(
        "experiment-" + "2" * 24,
        _sha("unsafe-experiment"),
        "problem-revision-r1",
        _sha("problem-r1"),
        "BLOCKED_SAFETY",
        ("evidence-hard-hazard",),
        1000000,
        1000000,
    )
    proposal = propose_experiment_selection(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("problem-r1"),
        candidates=(unsafe, eligible),
        selection_policy_id="policy-info-gain-v1",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=("evidence-selection-basis",),
    )
    assert proposal.selected_experiment_id == eligible.experiment_id
    assert proposal.selected_experiment_id != unsafe.experiment_id


def test_selection_is_deterministic_and_uses_information_gain_then_uncertainty_reduction():
    common = dict(
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("problem-r1"),
        constraint_status="ELIGIBLE",
        constraint_assessment_evidence_ids=("evidence-gates",),
    )
    a = ExperimentSelectionCandidate("experiment-" + "a" * 24, _sha("a"), expected_information_gain_ppm=600000, expected_uncertainty_reduction_ppm=100000, **common)
    b = ExperimentSelectionCandidate("experiment-" + "b" * 24, _sha("b"), expected_information_gain_ppm=600000, expected_uncertainty_reduction_ppm=900000, **common)
    proposal = propose_experiment_selection(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("problem-r1"),
        candidates=(a, b),
        selection_policy_id="policy-info-gain-v1",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=("evidence-selection-basis",),
    )
    assert proposal.selected_experiment_id == b.experiment_id


def test_no_eligible_experiment_produces_no_selection_not_a_fake_success():
    blocked = ExperimentSelectionCandidate(
        "experiment-" + "c" * 24,
        _sha("blocked"),
        "problem-revision-r1",
        _sha("problem-r1"),
        "BLOCKED_RESOURCE",
        ("evidence-resource-block",),
        900000,
        900000,
    )
    proposal = propose_experiment_selection(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("problem-r1"),
        candidates=(blocked,),
        selection_policy_id="policy-info-gain-v1",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=("evidence-selection-basis",),
    )
    assert proposal.selected_candidate_id == ""
    assert proposal.selected_experiment_id == ""


def test_selection_candidate_scores_are_integer_ppm_not_binary_float():
    with pytest.raises(TypeError, match="integer parts-per-million"):
        ExperimentSelectionCandidate(
            "experiment-" + "d" * 24,
            _sha("float-score"),
            "problem-revision-r1",
            _sha("problem-r1"),
            "ELIGIBLE",
            ("evidence-gates",),
            0.5,
            500000,
        )
