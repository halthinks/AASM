from aasm import AASMEngine, ProblemSpec, SQLiteStore
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


def test_review_gate_uses_deterministic_policy_for_benign_actions():
    gate=ReviewGatePolicy()
    assert gate.decide("test")["requires_model_review"] is False
    assert gate.decide("destructive")["requires_model_review"] is True
    assert gate.decide("read",assumption_changed=True)["requires_model_review"] is True
    assert gate.decide("build",tests_failed=True)["requires_model_review"] is True


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
