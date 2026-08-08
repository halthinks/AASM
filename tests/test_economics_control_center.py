from aasm import AASMEngine, ProblemSpec, SQLiteStore, CodexGovernancePolicy, import_otel_events
from aasm.economics import CallPurpose, EconomicsLedger, ModelPricing, ModelUsageRecord, ReviewGatePolicy


def test_cache_adjusted_economics_and_governance_ratio():
    pricing={"sol":ModelPricing("sol",5.0,.5,30.0)}
    ledger=EconomicsLedger()
    ledger.add(ModelUsageRecord("sol",CallPurpose.PRODUCTIVE.value,input_tokens=100_000,cached_input_tokens=80_000,output_tokens=10_000))
    ledger.add(ModelUsageRecord("sol",CallPurpose.PERMISSION_REVIEW.value,input_tokens=50_000,cached_input_tokens=0,output_tokens=2_000))
    summary=ledger.summary(pricing)
    assert summary["estimated_cost"] > 0
    assert 0 < summary["governance_cost_ratio"] < 1
    assert summary["by_purpose"]["permission_review"]["calls"] == 1


def test_unpriced_internal_model_is_not_silently_zero_cost():
    ledger=EconomicsLedger([{"model_id":"codex-auto-review","purpose":"permission_review","input_tokens":5000,"output_tokens":100}])
    summary=ledger.summary({})
    assert summary["unpriced_tokens"] == 5100
    assert summary["unpriced_models"] == ["codex-auto-review"]
    assert summary["cost_complete"] is False
    assert summary["governance_cost_ratio"] is None


def test_codex_otel_auto_review_is_classified_as_permission_review():
    batch=import_otel_events([
        {"model":"codex-auto-review","session_source":"subagent_guardian","token_type":"input","value":4000},
        {"model":"codex-auto-review","session_source":"subagent_guardian","token_type":"cached_input","value":2500},
        {"model":"codex-auto-review","session_source":"subagent_guardian","token_type":"output","value":500},
    ])
    assert len(batch.records)==1
    record=batch.records[0]
    assert record.purpose=="permission_review"
    assert record.input_tokens==6500
    assert record.cached_input_tokens==2500
    assert record.output_tokens==500


def test_review_gate_uses_deterministic_policy_for_benign_actions():
    gate=ReviewGatePolicy()
    assert gate.decide("test")["requires_model_review"] is False
    assert gate.decide("destructive")["requires_model_review"] is True
    assert gate.decide("read",assumption_changed=True)["requires_model_review"] is True
    assert gate.decide("build",tests_failed=True)["requires_model_review"] is True


def test_generated_codex_policy_keeps_sandbox_and_narrow_allowlist():
    policy=CodexGovernancePolicy()
    rules=policy.render_rules()
    requirements=policy.render_requirements_toml()
    assert "git', 'status" in rules
    assert "git', 'reset', '--hard" in rules
    assert "workspace-write" in requirements
    assert "open network" not in requirements.lower()


def test_economics_is_durable_and_dashboard_exposes_it(tmp_path):
    store=SQLiteStore(tmp_path/"econ.db")
    engine=AASMEngine(ProblemSpec("economics"),store=store)
    engine.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PRODUCTIVE.value,input_tokens=1000,output_tokens=500,task_id="t1"))
    engine.record_model_usage(ModelUsageRecord("gpt-5.6-sol",CallPurpose.VERIFICATION.value,input_tokens=1000,output_tokens=200,task_id="t1"))
    engine.review_gate("test")
    mid=engine.snapshot.machine_id
    resumed=AASMEngine.resume(mid,store)
    dash=resumed.dashboard()
    assert dash["economics"]["calls"] == 2
    assert dash["economics"]["governance_token_ratio"] > 0
    assert dash["machine_id"] == mid
    store.close()


def test_user_interrupt_is_provenance_not_hidden_prompt_state(tmp_path):
    store=SQLiteStore(tmp_path/"control.db")
    engine=AASMEngine(ProblemSpec("steer"),store=store)
    engine.user_interrupt("Add verification before commit",metadata={"source":"user"})
    mid=engine.snapshot.machine_id
    resumed=AASMEngine.resume(mid,store)
    assert resumed.snapshot.metadata["control"]["interrupts"][-1]["note"].startswith("Add verification")
    assert any(e.event_type=="user_interrupt" for e in resumed.events)
    store.close()
