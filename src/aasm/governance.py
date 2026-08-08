from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any

from .economics import CallPurpose, ReviewGatePolicy


class GovernanceAction:
    REVIEW_NOT_REQUIRED = "REVIEW_NOT_REQUIRED"
    MODEL_REVIEW_REQUIRED = "MODEL_REVIEW_REQUIRED"
    REVIEW_REUSED = "REVIEW_REUSED"
    BUDGET_PAUSE = "BUDGET_PAUSE"


@dataclass
class GovernanceBudgetPolicy:
    """Budget semantic-review overhead without weakening technical authority."""
    soft_governance_token_ratio: float | None = 0.35
    hard_governance_token_ratio: float | None = 0.75
    soft_governance_cost_ratio: float | None = 0.35
    hard_governance_cost_ratio: float | None = 0.75
    min_total_tokens_for_ratio_enforcement: int = 50_000
    max_governance_tokens: int | None = None
    max_governance_cost: float | None = None
    max_permission_review_calls: int | None = None
    enabled: bool = True

    def __post_init__(self):
        for name in ("soft_governance_token_ratio","hard_governance_token_ratio","soft_governance_cost_ratio","hard_governance_cost_ratio"):
            value=getattr(self,name)
            if value is not None and not 0 <= float(value) <= 1: raise ValueError(f"{name} must be between 0 and 1")
        if int(self.min_total_tokens_for_ratio_enforcement) < 0: raise ValueError("min_total_tokens_for_ratio_enforcement must be non-negative")
        for name in ("max_governance_tokens","max_permission_review_calls"):
            value=getattr(self,name)
            if value is not None and int(value) < 0: raise ValueError(f"{name} must be non-negative")
        if self.max_governance_cost is not None and float(self.max_governance_cost) < 0: raise ValueError("max_governance_cost must be non-negative")
        if self.soft_governance_token_ratio is not None and self.hard_governance_token_ratio is not None and self.soft_governance_token_ratio > self.hard_governance_token_ratio: raise ValueError("soft token ratio cannot exceed hard token ratio")
        if self.soft_governance_cost_ratio is not None and self.hard_governance_cost_ratio is not None and self.soft_governance_cost_ratio > self.hard_governance_cost_ratio: raise ValueError("soft cost ratio cannot exceed hard cost ratio")


@dataclass
class GovernanceContext:
    action_class: str
    scope: str = ""
    action_signature: str = ""
    policy_revision: str = "1"
    assumption_revision: str = ""
    evidence_revision: str = ""
    assumption_changed: bool = False
    tests_failed: bool = False
    diff_lines: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        payload={"action_class":self.action_class,"scope":self.scope,"action_signature":self.action_signature,"policy_revision":self.policy_revision,"assumption_revision":self.assumption_revision,"evidence_revision":self.evidence_revision}
        return sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


@dataclass
class GovernanceDecision:
    action: str
    requires_model_review: bool
    reason: str
    fingerprint: str
    budget_state: str = "OK"
    coalesced: bool = False
    review_model_hint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)


class GovernanceEconomicsController:
    """Deterministic semantic-review gate plus overhead/budget accounting."""
    NON_REUSABLE_RISK_CLASSES={"destructive","credential","security_sensitive","external_write","network_unknown","irreversible"}

    def __init__(self,review_policy:ReviewGatePolicy|None=None,budget:GovernanceBudgetPolicy|None=None,decisions:list[dict[str,Any]]|None=None):
        self.review_policy=review_policy or ReviewGatePolicy(); self.budget=budget or GovernanceBudgetPolicy(); self.decisions=[dict(x) for x in (decisions or [])]

    @staticmethod
    def _governance_bucket(summary):
        purposes=summary.get("by_purpose",{}) or {}; keys={CallPurpose.GOVERNANCE.value,CallPurpose.PERMISSION_REVIEW.value,CallPurpose.VERIFICATION.value}
        return {"tokens":sum(int((purposes.get(k) or {}).get("tokens",0) or 0) for k in keys),"cost":sum(float((purposes.get(k) or {}).get("estimated_cost",0) or 0) for k in keys),"permission_review_calls":int((purposes.get(CallPurpose.PERMISSION_REVIEW.value) or {}).get("calls",0) or 0)}

    def budget_status(self,economics_summary):
        gov=self._governance_bucket(economics_summary)
        if not self.budget.enabled: return {"state":"OK","reasons":[],"governance":gov,"ratio_enforced":False}
        reasons=[]; hard=[]; total_tokens=int(economics_summary.get("tokens",0) or 0); ratio_enforced=total_tokens>=self.budget.min_total_tokens_for_ratio_enforcement
        if ratio_enforced:
            token_ratio=float(economics_summary.get("governance_token_ratio",0) or 0); cost_ratio=economics_summary.get("governance_cost_ratio")
            if self.budget.soft_governance_token_ratio is not None and token_ratio>=self.budget.soft_governance_token_ratio: reasons.append("soft governance token ratio")
            if self.budget.hard_governance_token_ratio is not None and token_ratio>=self.budget.hard_governance_token_ratio: hard.append("hard governance token ratio")
            if cost_ratio is not None:
                if self.budget.soft_governance_cost_ratio is not None and cost_ratio>=self.budget.soft_governance_cost_ratio: reasons.append("soft governance cost ratio")
                if self.budget.hard_governance_cost_ratio is not None and cost_ratio>=self.budget.hard_governance_cost_ratio: hard.append("hard governance cost ratio")
        if self.budget.max_governance_tokens is not None and gov["tokens"]>=self.budget.max_governance_tokens: hard.append("governance token budget exhausted")
        if self.budget.max_governance_cost is not None and economics_summary.get("cost_complete") and gov["cost"]>=self.budget.max_governance_cost: hard.append("governance cost budget exhausted")
        if self.budget.max_permission_review_calls is not None and gov["permission_review_calls"]>=self.budget.max_permission_review_calls: hard.append("permission-review call budget exhausted")
        state="HARD" if hard else "SOFT" if reasons else "OK"
        return {"state":state,"reasons":hard+reasons if hard else reasons,"governance":gov,"ratio_enforced":ratio_enforced}

    def _matching_reusable_review(self,fingerprint):
        for decision in reversed(self.decisions):
            if decision.get("fingerprint")==fingerprint and decision.get("action")==GovernanceAction.MODEL_REVIEW_REQUIRED and decision.get("review_completed") is True: return decision
        return None

    def decide(self,context:GovernanceContext,economics_summary):
        base=self.review_policy.decide(context.action_class,assumption_changed=context.assumption_changed,tests_failed=context.tests_failed,diff_lines=context.diff_lines); fingerprint=context.fingerprint(); budget=self.budget_status(economics_summary)
        if not base["requires_model_review"]: return GovernanceDecision(GovernanceAction.REVIEW_NOT_REQUIRED,False,base["reason"],fingerprint,budget_state=budget["state"])
        reusable=None if context.action_class in self.NON_REUSABLE_RISK_CLASSES or context.assumption_changed or context.tests_failed else self._matching_reusable_review(fingerprint)
        if reusable is not None: return GovernanceDecision(GovernanceAction.REVIEW_REUSED,False,"unchanged previously-reviewed governance fingerprint",fingerprint,budget_state=budget["state"],coalesced=True,metadata={"reused_decision_id":reusable.get("decision_id")})
        if budget["state"]=="HARD": return GovernanceDecision(GovernanceAction.BUDGET_PAUSE,True,"required semantic review blocked by hard governance budget; authority is not granted",fingerprint,budget_state="HARD",metadata={"budget_reasons":budget["reasons"]})
        return GovernanceDecision(GovernanceAction.MODEL_REVIEW_REQUIRED,True,base["reason"],fingerprint,budget_state=budget["state"],review_model_hint="lower_cost_reviewer" if budget["state"]=="SOFT" else None)

    def report(self,economics_summary):
        budget=self.budget_status(economics_summary); counts={}
        for d in self.decisions: counts[d.get("action","UNKNOWN")]=counts.get(d.get("action","UNKNOWN"),0)+1
        return {"budget":budget,"decision_counts":counts,"coalesced_reviews":sum(1 for d in self.decisions if d.get("coalesced")),"decisions":len(self.decisions)}
