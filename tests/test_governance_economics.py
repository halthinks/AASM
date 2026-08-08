import threading
from http.server import ThreadingHTTPServer

from aasm import (
    AASMEngine,
    AASMRemoteClient,
    GovernanceAction,
    GovernanceBudgetPolicy,
    GovernanceContext,
    ModelUsageRecord,
    ProblemSpec,
    SQLiteStore,
)
from aasm.economics import CallPurpose
from aasm.server import make_handler


def test_benign_action_uses_deterministic_policy_without_model_review():
    e=AASMEngine(ProblemSpec("governance"))
    d=e.governance_decide(GovernanceContext("read",scope="repo",action_signature="git-status"))
    assert d["action"]==GovernanceAction.REVIEW_NOT_REQUIRED
    assert d["requires_model_review"] is False


def test_completed_low_risk_review_is_reused_only_for_identical_fingerprint():
    e=AASMEngine(ProblemSpec("reuse"))
    ctx=GovernanceContext("architecture_choice",scope="module-a",action_signature="choice-v1",assumption_revision="a1",evidence_revision="e1")
    first=e.governance_decide(ctx)
    assert first["action"]==GovernanceAction.MODEL_REVIEW_REQUIRED
    e.complete_governance_review(first["decision_id"],evidence=["review:accepted"])
    second=e.governance_decide(ctx)
    assert second["action"]==GovernanceAction.REVIEW_REUSED
    assert second["requires_model_review"] is False
    changed=e.governance_decide(GovernanceContext("architecture_choice",scope="module-a",action_signature="choice-v1",assumption_revision="a2",evidence_revision="e1"))
    assert changed["action"]==GovernanceAction.MODEL_REVIEW_REQUIRED


def test_high_risk_review_is_never_reused():
    e=AASMEngine(ProblemSpec("risk"))
    ctx=GovernanceContext("external_write",scope="production",action_signature="deploy")
    first=e.governance_decide(ctx); e.complete_governance_review(first["decision_id"],evidence=["approved"])
    second=e.governance_decide(ctx)
    assert second["action"]==GovernanceAction.MODEL_REVIEW_REQUIRED
    assert second["coalesced"] is False


def test_ratio_budget_waits_for_minimum_observed_tokens():
    e=AASMEngine(ProblemSpec("sample floor"))
    e.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PERMISSION_REVIEW.value,input_tokens=1000,output_tokens=100))
    d=e.governance_decide(GovernanceContext("architecture_choice",action_signature="x"))
    assert d["budget_state"]=="OK"
    assert d["action"]==GovernanceAction.MODEL_REVIEW_REQUIRED
    assert e.governance_report()["budget"]["ratio_enforced"] is False


def test_hard_budget_pauses_instead_of_waiving_required_review():
    e=AASMEngine(ProblemSpec("hard budget"))
    e.configure_governance_budget(GovernanceBudgetPolicy(max_permission_review_calls=1,min_total_tokens_for_ratio_enforcement=999999))
    e.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PERMISSION_REVIEW.value,input_tokens=1000,output_tokens=100))
    d=e.governance_decide(GovernanceContext("architecture_choice",action_signature="x"))
    assert d["action"]==GovernanceAction.BUDGET_PAUSE
    assert d["requires_model_review"] is True
    assert "authority is not granted" in d["reason"]


def test_soft_budget_suggests_lower_cost_reviewer_not_less_review():
    e=AASMEngine(ProblemSpec("soft budget"))
    e.configure_governance_budget(GovernanceBudgetPolicy(soft_governance_token_ratio=.2,hard_governance_token_ratio=.9,soft_governance_cost_ratio=None,hard_governance_cost_ratio=None,min_total_tokens_for_ratio_enforcement=1000))
    e.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PRODUCTIVE.value,input_tokens=5000,output_tokens=1000))
    e.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PERMISSION_REVIEW.value,input_tokens=3000,output_tokens=1000))
    d=e.governance_decide(GovernanceContext("architecture_choice",action_signature="x"))
    assert d["budget_state"]=="SOFT"
    assert d["requires_model_review"] is True
    assert d["review_model_hint"]=="lower_cost_reviewer"


def test_avoided_overhead_uses_observed_permission_review_baseline():
    e=AASMEngine(ProblemSpec("avoided"))
    e.record_model_usage(ModelUsageRecord("gpt-5.6-luna",CallPurpose.PERMISSION_REVIEW.value,input_tokens=1000,output_tokens=100))
    ctx=GovernanceContext("architecture_choice",action_signature="stable")
    first=e.governance_decide(ctx); e.complete_governance_review(first["decision_id"])
    reused=e.governance_decide(ctx)
    assert reused["action"]==GovernanceAction.REVIEW_REUSED
    report=e.governance_report()
    assert report["avoided_overhead"]["reused_review_calls"]==1
    assert report["avoided_overhead"]["estimated_avoided_tokens_from_reuse"]==1100


def test_governance_state_survives_restart(tmp_path):
    db=tmp_path/"gov.db"; store=SQLiteStore(db); e=AASMEngine(ProblemSpec("persist governance"),store=store)
    e.configure_governance_budget(GovernanceBudgetPolicy(max_governance_tokens=50000))
    first=e.governance_decide(GovernanceContext("architecture_choice",action_signature="stable")); e.complete_governance_review(first["decision_id"],evidence=["ok"]); mid=e.snapshot.machine_id; store.close()
    store=SQLiteStore(db); resumed=AASMEngine.resume(mid,store)
    assert resumed.governance_controller.budget.max_governance_tokens==50000
    assert resumed.governance_decide(GovernanceContext("architecture_choice",action_signature="stable"))["action"]==GovernanceAction.REVIEW_REUSED
    store.close()


def test_remote_governance_feedback_roundtrip(tmp_path):
    db=str(tmp_path/"remote-gov.db"); store=SQLiteStore(db); e=AASMEngine(ProblemSpec("remote governance"),store=store); mid=e.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret")); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        client.configure_governance_budget(mid,GovernanceBudgetPolicy(max_permission_review_calls=10))
        first=client.governance_decide(mid,GovernanceContext("architecture_choice",action_signature="remote"))
        client.complete_governance_review(mid,first["decision_id"],["remote-review"])
        second=client.governance_decide(mid,GovernanceContext("architecture_choice",action_signature="remote"))
        assert second["action"]==GovernanceAction.REVIEW_REUSED
        assert client.state(mid)["governance"]["coalesced_reviews"]==1
    finally:
        server.shutdown(); server.server_close()
