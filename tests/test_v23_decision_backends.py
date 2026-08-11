from __future__ import annotations

import pytest

from aasm import (
    AASMEngine,
    BackendBudget,
    CallbackDecisionBackend,
    DecisionBackendRegistry,
    DecisionRecord,
    DecisionRequest,
    FiniteDomainDecisionBackend,
    ProblemSpec,
)


def _request():
    return DecisionRequest(
        machine_id="m",
        profile_binding={},
        active_model={},
        available_decisions=[
            {"decision_id": "D-a", "subject": "method", "value": "A", "status": "PROPOSED"},
            {"decision_id": "D-b", "subject": "method", "value": "B", "status": "PROPOSED"},
            {"decision_id": "D-n", "subject": "site", "value": "north", "status": "PROPOSED"},
            {"decision_id": "D-s", "subject": "site", "value": "south", "status": "PROPOSED"},
        ],
    )


def test_finite_domain_backend_is_deterministic_and_continuable():
    backend = FiniteDomainDecisionBackend()
    first = backend.propose_batch(_request(), budget=BackendBudget(max_candidates=2))
    again = backend.propose_batch(_request(), budget=BackendBudget(max_candidates=2))
    first_data = first.to_dict()
    again_data = again.to_dict()
    first_data["usage"]["latency_ms"] = 0.0
    again_data["usage"]["latency_ms"] = 0.0
    assert first_data == again_data
    assert len(first.candidates) == 2
    assert first.exhausted is False
    second = backend.propose_batch(
        _request(), budget=BackendBudget(max_candidates=2), continuation=first.continuation
    )
    assert second.exhausted is True
    first_assignments = {tuple(sorted(candidate.assignments.items())) for candidate in first.candidates}
    second_assignments = {tuple(sorted(candidate.assignments.items())) for candidate in second.candidates}
    assert first_assignments.isdisjoint(second_assignments)
    assert len(first_assignments | second_assignments) == 4


def test_runtime_records_validates_selects_and_activates_candidates():
    engine = AASMEngine(ProblemSpec("choose a method"))
    engine.register_decision(DecisionRecord("D-a", "method", "A"))
    engine.register_decision(DecisionRecord("D-b", "method", "B"))
    batch = engine.generate_candidate_batch(
        "aasm.finite-domain",
        budget=BackendBudget(max_candidates=2),
    )
    assert len(batch["candidates"]) == 2
    records = engine.candidate_records(status="ADMISSIBLE")
    assert len(records) == 2
    candidate_id = records[0]["candidate"]["candidate_id"]
    engine.select_candidate(candidate_id)
    result = engine.activate_candidate(candidate_id)
    assert result["candidate"]["status"] == "ACTIVATED"
    assert engine.backend_report()["activated_candidate_id"] == candidate_id
    assert engine.calculus_report()["active_model"]["method"] in {"D-a", "D-b"}


def test_candidate_activation_is_all_or_nothing_when_a_late_assignment_fails():
    def candidate(_request):
        return [{
            "candidate_id": "candidate-atomic",
            "assignments": {"backend": "D-new", "adapter": "D-child"},
        }]

    registry = DecisionBackendRegistry()
    registry.register(CallbackDecisionBackend(candidate, backend_id="test.atomic"))
    engine = AASMEngine(ProblemSpec("atomic activation"), backend_registry=registry)
    engine.register_decision(DecisionRecord("D-old", "backend", "old", level=1))
    engine.activate_decision("D-old")
    engine.register_decision(DecisionRecord("D-new", "backend", "new", level=1))
    engine.register_decision(DecisionRecord(
        "D-child",
        "adapter",
        "old-adapter",
        kind="DERIVED",
        level=2,
        parent_ids=["D-old"],
    ))
    engine.generate_candidate_batch("test.atomic")

    before = engine.calculus_report()
    with pytest.raises(ValueError, match="parents inactive"):
        engine.activate_candidate("candidate-atomic")
    after = engine.calculus_report()

    assert before["active_model"] == {"backend": "D-old"}
    assert after["active_model"] == before["active_model"]
    assert after["decisions"]["D-old"]["status"] == "ACTIVE"
    assert after["decisions"]["D-new"]["status"] == "PROPOSED"
    assert engine.candidate_records()[0]["status"] == "ADMISSIBLE"
