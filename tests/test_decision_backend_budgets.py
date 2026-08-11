import time

from aasm.decision_backends import (
    BackendBudget,
    CallbackDecisionBackend,
    FiniteDomainDecisionBackend,
    PortfolioDecisionBackend,
)


def test_finite_domain_is_incremental_not_all_or_nothing():
    backend = FiniteDomainDecisionBackend()
    request = {"request_id": "r", "domains": {"a": ["1", "2"], "b": ["x", "y"]}}
    first = backend.generate(request, budget=BackendBudget(max_candidates=2, max_combinations=2))
    assert len(first.candidates) == 2
    assert first.exhausted is False
    assert first.continuation
    second = backend.generate(
        request,
        budget=BackendBudget(max_candidates=2, max_combinations=2),
        continuation=first.continuation,
    )
    assert len(second.candidates) == 2
    assert second.exhausted is True
    assert {c.candidate_id for c in first.candidates}.isdisjoint(
        {c.candidate_id for c in second.candidates}
    )


def test_callback_timeout_becomes_explicit_diagnostic():
    def slow(_request):
        time.sleep(0.1)
        return []

    backend = CallbackDecisionBackend(slow)
    batch = backend.generate(
        {"request_id": "r"},
        budget=BackendBudget(max_latency_ms=10),
    )
    assert batch.candidates == []
    assert any(row.code == "CALLBACK_TIMEOUT" for row in batch.diagnostics)


def test_portfolio_aggregates_duplicate_provenance():
    def one(_request):
        return [{"candidate_id": "a", "assignments": {"x": "d1"}}]

    def two(_request):
        return [{"candidate_id": "b", "assignments": {"x": "d1"}}]

    portfolio = PortfolioDecisionBackend([
        CallbackDecisionBackend(one, backend_id="one"),
        CallbackDecisionBackend(two, backend_id="two"),
    ])
    batch = portfolio.generate({}, budget=BackendBudget(max_candidates=10))
    assert len(batch.candidates) == 1
    sources = batch.candidates[0].to_dict()["metadata"]["portfolio_sources"]
    assert {row["backend_id"] for row in sources} == {"one", "two"}
