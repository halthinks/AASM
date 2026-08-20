from __future__ import annotations

import pytest

from aasm.evidence import EvidenceRecord
from aasm.experiment import (
    ExperimentContextBinding,
    ExperimentHypothesis,
    ExperimentOutcomeCriterion,
    ExperimentProcedureStep,
    ExperimentSelectionCandidate,
    ExperimentSelectionProposal,
    ExperimentSpec,
    ExperimentVariable,
    propose_experiment_selection,
)
from aasm.experiment_runtime import ExperimentRuntimeMixin
from aasm.model import ProblemSpec
from aasm.runtime_v56_foundation import AASMEngine as V56FoundationEngine
from aasm.semantic_dependencies import SemanticNodeRef
from aasm.semantic_evolution import ProblemDelta, ProblemRevision
from aasm.semantic_result import semantic_fingerprint


class ExperimentEngine(ExperimentRuntimeMixin, V56FoundationEngine):
    pass


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _engine() -> ExperimentEngine:
    return ExperimentEngine(ProblemSpec("S5.2 durable governed experiments"))


def _base() -> ProblemRevision:
    return ProblemRevision(
        problem_id="pcb-main",
        problem_fingerprint=_sha("problem-v1"),
        semantic_projection_fingerprint=_sha("projection-v1"),
        environment_fingerprint=_sha("environment-v1"),
        dependency_fingerprints=(_sha("dependency-v1"),),
        created_by="controller-c",
        revision_id="problem-revision-r1",
    )


def _evidence(engine: ExperimentEngine) -> dict[str, EvidenceRecord]:
    names = (
        "diagnosis", "hypothesis", "environment", "evidence-floor", "risk",
        "resource", "verification", "constraint-gates", "selection-policy",
    )
    return {
        name: engine.add_evidence(EvidenceRecord("observation", name, source="test"))
        for name in names
    }


def _bound(kind: str, label: str, contract: str, evidence_id: str) -> ExperimentContextBinding:
    return ExperimentContextBinding(
        kind,
        "BOUND",
        contract_id=contract,
        object_id=f"{kind.lower()}-{label}",
        object_fingerprint=_sha(f"{kind}-{label}"),
        evidence_ids=(evidence_id,),
    )


def _spec(base: ProblemRevision, rows: dict[str, EvidenceRecord], name: str = "experiment-a") -> ExperimentSpec:
    h1 = ExperimentHypothesis(
        "geometry is causal",
        semantic_refs=(SemanticNodeRef("CONSTRAINT", "clearance"),),
        basis_evidence_ids=(rows["hypothesis"].evidence_id,),
    )
    h2 = ExperimentHypothesis(
        "manufacturing assumption is causal",
        semantic_refs=(SemanticNodeRef("RULE", "manufacturing"),),
        basis_evidence_ids=(rows["hypothesis"].evidence_id,),
    )
    return ExperimentSpec(
        experiment_name=name,
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id=base.revision_id,
        problem_revision_fingerprint=base.fingerprint,
        hypotheses=(h1, h2),
        variables=(
            ExperimentVariable("control", "CONTROLLED", SemanticNodeRef("CONSTRAINT", "control-clearance"), _sha("control")),
            ExperimentVariable("measure", "MEASURED", SemanticNodeRef("EVIDENCE", "measure-drc"), _sha("measure")),
        ),
        procedure_steps=(
            ExperimentProcedureStep("prepare", 0, "prepare exact revision"),
            ExperimentProcedureStep("verify", 1, "run declared verifier"),
        ),
        context_bindings=(
            _bound("ENVIRONMENT", "sim", "aasm.execution.environment-binding.v1", rows["environment"].evidence_id),
            ExperimentContextBinding("FIXTURE_IDENTITY", "NOT_APPLICABLE", reason="simulation-only"),
            ExperimentContextBinding("CALIBRATION_IDENTITY", "NOT_APPLICABLE", reason="simulation-only"),
            _bound("EVIDENCE_FLOOR", "policy", "aasm.evidence.policy.v1", rows["evidence-floor"].evidence_id),
            _bound("RISK_CONSTRAINT", "risk", "aasm.risk.assessment.v1", rows["risk"].evidence_id),
            _bound("RESOURCE_DEMAND", "resource", "aasm.resource.demand.v1", rows["resource"].evidence_id),
            _bound("VERIFICATION_OBLIGATION", "verify", "aasm.obligation.phase.v1", rows["verification"].evidence_id),
        ),
        outcome_criteria=(
            ExperimentOutcomeCriterion("geometry", "geometry discriminates", _sha("outcome-geometry"), supports_hypothesis_ids=(h1.hypothesis_id,), contradicts_hypothesis_ids=(h2.hypothesis_id,)),
            ExperimentOutcomeCriterion("manufacturing", "manufacturing discriminates", _sha("outcome-manufacturing"), supports_hypothesis_ids=(h2.hypothesis_id,), contradicts_hypothesis_ids=(h1.hypothesis_id,)),
        ),
        producer_principal_id="planner-a",
        evidence_ids=(rows["diagnosis"].evidence_id,),
    )


def _setup():
    engine = _engine()
    rows = _evidence(engine)
    base = _base()
    engine.register_initial_problem_revision(base, authority_id="controller-c", authority_class="CONTROLLER")
    spec = _spec(base, rows)
    return engine, rows, base, spec


def _candidate(spec: ExperimentSpec, gate_evidence_id: str, *, status="ELIGIBLE", info=700000, uncertainty=500000) -> ExperimentSelectionCandidate:
    return ExperimentSelectionCandidate(
        spec.experiment_id,
        spec.fingerprint,
        spec.problem_revision_id,
        spec.problem_revision_fingerprint,
        status,
        (gate_evidence_id,),
        info,
        uncertainty,
    )


def test_runtime_contract_is_durable_but_still_proposal_only():
    engine = _engine()
    contract = engine.experiment_runtime_contract_report()
    assert contract["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert contract["problem_revision_source"] == "EXISTING_AASM_SEMANTIC_EVOLUTION_ONLY"
    assert contract["experiment_execution"] == "NONE"
    assert contract["effect_dispatch"] == "NONE"
    assert contract["resource_reservation"] == "NONE"
    assert contract["problem_mutation"] == "NONE"
    assert contract["parallel_experiment_store"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_experiment_spec_records_replays_and_does_not_mutate_problem_revision():
    engine, _, base, spec = _setup()
    before = engine.semantic_evolution_report(base.problem_id)
    recorded = engine.record_experiment_spec(spec)
    assert recorded["already_recorded"] is False
    assert engine.record_experiment_spec(spec)["already_recorded"] is True
    report = engine.experiment_report()
    assert report["valid"] is True, report["issues"]
    assert report["experiments"][spec.experiment_id]["experiment"]["fingerprint"] == spec.fingerprint
    after = engine.semantic_evolution_report(base.problem_id)
    assert before["heads"] == after["heads"] == [base.revision_id]
    assert after["transitions"] == {}
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_stale_problem_revision_blocks_new_experiment_record():
    engine, rows, base, spec = _setup()
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint=_sha("problem-v2"),
        target_semantic_projection_fingerprint=_sha("projection-v2"),
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint=delta.target_problem_fingerprint,
        semantic_projection_fingerprint=delta.target_semantic_projection_fingerprint,
        parent_revision_ids=(base.revision_id,),
        environment_fingerprint=base.environment_fingerprint,
        dependency_fingerprints=base.dependency_fingerprints,
        created_by="controller-c",
        created_from_delta_id=delta.delta_id,
        revision_id="problem-revision-r2",
    )
    engine.commit_problem_revision_transition(delta, target, authority_id="controller-c", authority_class="CONTROLLER")
    with pytest.raises(ValueError, match="STALE_EXPERIMENT_PROBLEM_REVISION"):
        engine.record_experiment_spec(spec)


def test_invalidated_support_blocks_new_experiment_but_does_not_erase_history():
    engine, rows, _, spec = _setup()
    recorded = engine.record_experiment_spec(spec)
    engine.invalidate_evidence(rows["risk"].evidence_id, "risk assessment superseded")
    report = engine.experiment_report()
    assert report["valid"] is True
    assert spec.experiment_id in report["experiments"]
    assert recorded["evidence_id"] == report["experiments"][spec.experiment_id]["evidence_id"]

    second = _spec(_base(), rows, name="experiment-b")
    with pytest.raises(PermissionError, match="STALE_EXPERIMENT_SUPPORT_EVIDENCE"):
        engine.record_experiment_spec(second)


def test_selection_requires_recorded_exact_experiment_identity():
    engine, rows, _, spec = _setup()
    candidate = _candidate(spec, rows["constraint-gates"].evidence_id)
    proposal = propose_experiment_selection(
        workspace_id=spec.workspace_id,
        scope_id=spec.scope_id,
        problem_revision_id=spec.problem_revision_id,
        problem_revision_fingerprint=spec.problem_revision_fingerprint,
        candidates=(candidate,),
        selection_policy_id="policy-info-gain",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=(rows["selection-policy"].evidence_id,),
    )
    with pytest.raises(KeyError, match="EXPERIMENT_SELECTION_UNKNOWN_EXPERIMENT"):
        engine.record_experiment_selection(proposal)


def test_selection_is_recomputed_and_cannot_choose_lower_information_value_candidate():
    engine, rows, base, first = _setup()
    second = _spec(base, rows, name="experiment-b")
    engine.record_experiment_spec(first)
    engine.record_experiment_spec(second)
    a = _candidate(first, rows["constraint-gates"].evidence_id, info=900000, uncertainty=100000)
    b = _candidate(second, rows["constraint-gates"].evidence_id, info=500000, uncertainty=900000)
    forged = ExperimentSelectionProposal(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id=base.revision_id,
        problem_revision_fingerprint=base.fingerprint,
        candidates=(a, b),
        selected_candidate_id=b.candidate_id,
        selection_policy_id="policy-info-gain",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=(rows["selection-policy"].evidence_id,),
    )
    with pytest.raises(ValueError, match="DETERMINISTIC_RECOMPUTATION_MISMATCH"):
        engine.record_experiment_selection(forged)
    assert engine.experiment_report()["selections"] == {}


def test_stale_constraint_assessment_evidence_blocks_new_selection():
    engine, rows, _, spec = _setup()
    engine.record_experiment_spec(spec)
    candidate = _candidate(spec, rows["constraint-gates"].evidence_id)
    proposal = propose_experiment_selection(
        workspace_id=spec.workspace_id,
        scope_id=spec.scope_id,
        problem_revision_id=spec.problem_revision_id,
        problem_revision_fingerprint=spec.problem_revision_fingerprint,
        candidates=(candidate,),
        selection_policy_id="policy-info-gain",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=(rows["selection-policy"].evidence_id,),
    )
    engine.invalidate_evidence(rows["constraint-gates"].evidence_id, "constraint assessment stale")
    with pytest.raises(PermissionError, match="STALE_EXPERIMENT_SUPPORT_EVIDENCE"):
        engine.record_experiment_selection(proposal)
    assert engine.experiment_report()["selections"] == {}


def test_durable_selection_remains_historical_after_support_later_invalidates():
    engine, rows, base, spec = _setup()
    engine.record_experiment_spec(spec)
    candidate = _candidate(spec, rows["constraint-gates"].evidence_id)
    recorded = engine.propose_and_record_experiment_selection(
        workspace_id=spec.workspace_id,
        scope_id=spec.scope_id,
        problem_revision_id=spec.problem_revision_id,
        problem_revision_fingerprint=spec.problem_revision_fingerprint,
        candidates=(candidate,),
        selection_policy_id="policy-info-gain",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=(rows["selection-policy"].evidence_id,),
    )
    engine.invalidate_evidence(rows["constraint-gates"].evidence_id, "later superseded")
    report = engine.experiment_report()
    assert report["valid"] is True
    assert recorded["selection"]["selection_id"] in report["selections"]
    assert engine.semantic_evolution_report(base.problem_id)["transitions"] == {}


def test_selection_record_never_reserves_resources_or_dispatches_effects():
    engine, rows, base, spec = _setup()
    engine.record_experiment_spec(spec)
    candidate = _candidate(spec, rows["constraint-gates"].evidence_id)
    engine.propose_and_record_experiment_selection(
        workspace_id=spec.workspace_id,
        scope_id=spec.scope_id,
        problem_revision_id=spec.problem_revision_id,
        problem_revision_fingerprint=spec.problem_revision_fingerprint,
        candidates=(candidate,),
        selection_policy_id="policy-info-gain",
        selection_policy_fingerprint=_sha("selection-policy"),
        producer_principal_id="planner-a",
        evidence_ids=(rows["selection-policy"].evidence_id,),
    )
    assert engine.semantic_evolution_report(base.problem_id)["transitions"] == {}
    assert engine.experiment_runtime_contract_report()["resource_reservation"] == "NONE"
    assert engine.experiment_runtime_contract_report()["effect_dispatch"] == "NONE"
