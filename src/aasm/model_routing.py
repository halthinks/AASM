from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ModelProfile:
    model_id: str
    provider: str
    capabilities: list[str] = field(default_factory=list)
    strength: float = 0.5
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    latency_score: float = 0.5
    context_window: int = 0
    enabled: bool = True
    max_concurrency: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.model_id: raise ValueError("model_id is required")
        if not self.provider: raise ValueError("provider is required")
        if not 0 <= float(self.strength) <= 1: raise ValueError("strength must be between 0 and 1")
        if not 0 <= float(self.latency_score) <= 1: raise ValueError("latency_score must be between 0 and 1")
        if self.cost_per_1k_input < 0 or self.cost_per_1k_output < 0: raise ValueError("model costs must be non-negative")
        if self.context_window < 0: raise ValueError("context_window must be non-negative")
        if self.max_concurrency is not None and self.max_concurrency < 1: raise ValueError("max_concurrency must be positive")
        self.capabilities=sorted(set(self.capabilities))


@dataclass
class ModelRouteRequest:
    task_id: str
    required_capabilities: list[str] = field(default_factory=list)
    min_strength: float = 0.0
    min_context_window: int = 0
    max_cost_per_1k_output: float | None = None
    optimize: str = "balanced"
    candidate_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.optimize not in {"balanced","strength","cost","latency"}: raise ValueError("optimize must be balanced, strength, cost, or latency")
        if not 0 <= float(self.min_strength) <= 1: raise ValueError("min_strength must be between 0 and 1")
        if self.min_context_window < 0: raise ValueError("min_context_window must be non-negative")
        self.required_capabilities=sorted(set(self.required_capabilities))


@dataclass
class ModelRouteResult:
    task_id: str
    selected_model_id: str | None
    provider: str | None
    score: float | None
    eligible: list[str] = field(default_factory=list)
    rejected: dict[str,list[str]] = field(default_factory=dict)
    reason: str = ""
    def to_dict(self): return asdict(self)


class ModelStrengthRouter:
    @staticmethod
    def _reasons(profile:ModelProfile, req:ModelRouteRequest):
        reasons=[]
        if not profile.enabled: reasons.append("disabled")
        if req.candidate_ids and profile.model_id not in req.candidate_ids: reasons.append("not_candidate")
        if not set(req.required_capabilities).issubset(profile.capabilities): reasons.append("missing_capability")
        if profile.strength + 1e-12 < req.min_strength: reasons.append("strength_below_floor")
        if profile.context_window < req.min_context_window: reasons.append("context_too_small")
        if req.max_cost_per_1k_output is not None and profile.cost_per_1k_output > req.max_cost_per_1k_output + 1e-12: reasons.append("cost_above_ceiling")
        return reasons

    @staticmethod
    def _score(profile:ModelProfile,optimize:str):
        cost_score=1.0/(1.0+float(profile.cost_per_1k_output))
        if optimize=="strength": return float(profile.strength)
        if optimize=="cost": return cost_score
        if optimize=="latency": return float(profile.latency_score)
        return 0.55*float(profile.strength)+0.25*cost_score+0.20*float(profile.latency_score)

    def route(self, profiles:list[ModelProfile], request:ModelRouteRequest):
        rejected={}; eligible=[]
        for p in profiles:
            reasons=self._reasons(p,request)
            if reasons: rejected[p.model_id]=reasons
            else: eligible.append(p)
        if not eligible: return ModelRouteResult(request.task_id,None,None,None,[],rejected,"no eligible model satisfies the routing contract")
        ranked=sorted(eligible,key=lambda p:(-self._score(p,request.optimize),p.cost_per_1k_output,-p.strength,p.model_id))
        best=ranked[0]
        return ModelRouteResult(request.task_id,best.model_id,best.provider,self._score(best,request.optimize),[p.model_id for p in ranked],rejected,f"selected by {request.optimize} objective after hard capability/strength/context/cost filters")
