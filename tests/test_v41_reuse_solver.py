from aasm import (
    AASMEngine,
    EvidenceRecord,
    ProblemSpec,
    ReuseCandidate,
    ReuseMetrics,
    ReuseRequest,
    SolverStepRequest,
    validate_public_api_contract,
)


def seeded_reuse_engine():
    engine = AASMEngine(ProblemSpec("v41-reuse"))
    source_evidence = engine.add_evidence(
        EvidenceRecord(kind="tool_observation", statement="alpha", source="test.v41"),
        reason="seed reusable evidence",
    )
    request = ReuseRequest(kind="TOOL_OBSERVATION", semantic_payload={"query": "alpha"})
    source = engine.canonical_reuse_ref("EVIDENCE", source_evidence.evidence_id)
    candidate = ReuseCandidate(
        kind=request.kind,
        request_fingerprint=request.fingerprint,
        source=source,
        semantic_payload=request.semantic_payload,
        reusable_modes=("EXACT",),
    )
    engine.register_reuse_candidate(
        candidate,
        authority_id="policy",
        authority_class="POLICY",
    )
    return engine, request


def test_v41_public_contract_and_reuse_report_are_live():
    report = validate_public_api_contract()
    assert report["valid"], report
    engine, _ = seeded_reuse_engine()
    projected = engine.reuse_report()
    assert projected["authority"] == "DURABLE_EVIDENCE_PROJECTION"
    assert projected["hot_index_authoritative"] is False
    assert projected["counts"] == {"candidates": 1, "certificates": 0, "metrics": 0}


def test_exact_reuse_survives_hot_index_deletion_and_commits_certificate():
    engine, request = seeded_reuse_engine()
    first = engine.lookup_reuse(request)
    assert first["hit"] is True
    assert first["validation"]["mode"] == "EXACT"

    engine._reuse_hot_index().clear()
    second = engine.lookup_reuse(request)
    assert second["hit"] is True
    committed = engine.commit_reuse_certificate(second, actor_id="test", authority_class="CONTROLLER")
    assert committed["certificate"]["equivalence_mode"] == "EXACT"
    assert engine.reuse_report()["counts"]["certificates"] == 1


def test_non_idempotent_effect_is_never_reused():
    engine, _ = seeded_reuse_engine()
    request = ReuseRequest(
        kind="TOOL_OBSERVATION",
        semantic_payload={"query": "alpha"},
        effect_class="NON_IDEMPOTENT_EFFECT",
    )
    result = engine.lookup_reuse(request)
    assert result["hit"] is False
    assert "non_idempotent_effect_never_reused" in result["rejections"][0]["reasons"]


def test_solver_loop_skips_execution_only_after_validated_reuse():
    engine, request = seeded_reuse_engine()
    result = engine.solver_step(SolverStepRequest(scope_id="root"), reuse_request=request)
    assert result["phase"] == "REUSE"
    assert result["status"] == "REUSED"
    assert result["action"] == "SKIP_EXECUTION"
    assert result["reuse_certificate_id"].startswith("reuse-cert-")


def test_reuse_metrics_use_the_runtime_mixin_and_are_durable():
    engine, _ = seeded_reuse_engine()
    engine.record_reuse_metrics(
        ReuseMetrics(attempts=1, exact_hits=1, model_calls_avoided=1),
        actor_id="test",
    )
    report = engine.reuse_report()
    assert report["counts"]["metrics"] == 1
    assert report["metrics"][0]["payload"]["model_calls_avoided"] == 1
