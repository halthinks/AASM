from __future__ import annotations

from aasm import (
    AASMEngine,
    BackendBudget,
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
    assert first.to_dict() == again.to_dict()
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
