from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import sqrt
from typing import Any

from .model_routing import ModelProfile, ModelRouteRequest, ModelRouteResult, ModelStrengthRouter


@dataclass
class ModelOutcomeRecord:
    task_id: str
    task_class: str
    model_id: str
    accepted: bool
    executor_id: str | None = None
    repair_required: bool = False
    verification_score: float | None = None
    latency_seconds: float | None = None
    estimated_cost: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.task_id or not self.task_class or not self.model_id:
            raise ValueError("task_id, task_class, and model_id are required")
        if self.verification_score is not None and not 0 <= float(self.verification_score) <= 1:
            raise ValueError("verification_score must be between 0 and 1")
        if self.latency_seconds is not None and self.latency_seconds < 0:
            raise ValueError("latency_seconds must be non-negative")
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated_cost must be non-negative")


@dataclass
class ModelPerformance:
    task_class: str
    model_id: str
    samples: int
    accepted: int
    repairs: int
    acceptance_rate: float
    acceptance_lower_bound: float
    repair_rate: float
    avg_verification_score: float | None
    avg_latency_seconds: float | None
    avg_estimated_cost: float | None
    confidence: float

    def to_dict(self): return asdict(self)


class ModelOutcomeLedger:
    def __init__(self, records: list[dict[str, Any]] | None = None):
        self.records=[ModelOutcomeRecord(**raw) for raw in (records or [])]
    def add(self,record:ModelOutcomeRecord): self.records.append(record); return record
    @staticmethod
    def _wilson_lower(successes:int,n:int,z:float=1.96):
        if n<=0: return 0.0
        p=successes/n; zz=z*z; denom=1+zz/n
        center=p+zz/(2*n); margin=z*sqrt((p*(1-p)+zz/(4*n))/n)
        return max(0.0,(center-margin)/denom)
    def performance(self,task_class:str|None=None):
        groups={}
        for r in self.records:
            if task_class is not None and r.task_class!=task_class: continue
            groups.setdefault((r.task_class,r.model_id),[]).append(r)
        out=[]
        for (tc,mid),rows in sorted(groups.items()):
            n=len(rows); accepted=sum(1 for r in rows if r.accepted); repairs=sum(1 for r in rows if r.repair_required)
            scores=[float(r.verification_score) for r in rows if r.verification_score is not None]
            latencies=[float(r.latency_seconds) for r in rows if r.latency_seconds is not None]
            costs=[float(r.estimated_cost) for r in rows if r.estimated_cost is not None]
            out.append(ModelPerformance(tc,mid,n,accepted,repairs,accepted/n,self._wilson_lower(accepted,n),repairs/n,sum(scores)/len(scores) if scores else None,sum(latencies)/len(latencies) if latencies else None,sum(costs)/len(costs) if costs else None,n/(n+5.0)))
        return out
    def to_dict(self): return [asdict(r) for r in self.records]


@dataclass
class AdaptiveRouteResult(ModelRouteResult):
    task_class: str | None = None
    adaptive: bool = False
    performance: dict[str, dict[str, Any]] = field(default_factory=dict)
    static_selected_model_id: str | None = None
    def to_dict(self): return asdict(self)


class AdaptiveModelRouter:
    """Refine static model routing using explicit evaluated outcomes.

    Static capability/strength/context/cost constraints remain hard gates.
    Empirical routing only ranks models that already satisfy those contracts.
    """
    def __init__(self,ledger:ModelOutcomeLedger,base_router:ModelStrengthRouter|None=None):
        self.ledger=ledger; self.base=base_router or ModelStrengthRouter()

    @staticmethod
    def _cost_efficiency(perf:ModelPerformance):
        if perf.avg_estimated_cost is None: return perf.acceptance_lower_bound
        return perf.acceptance_lower_bound/(1.0+perf.avg_estimated_cost)

    def route(self,profiles:list[ModelProfile],request:ModelRouteRequest):
        static=self.base.route(profiles,request)
        task_class=str(request.metadata.get("task_class") or "").strip() or None
        if not static.selected_model_id or not task_class:
            return AdaptiveRouteResult(**asdict(static),task_class=task_class,adaptive=False,performance={},static_selected_model_id=static.selected_model_id)

        min_samples=int(request.metadata.get("min_empirical_samples",3) or 0)
        acceptance_floor=float(request.metadata.get("min_empirical_acceptance",0.0) or 0.0)
        explore=bool(request.metadata.get("explore_under_sampled",False))
        optimize_empirical=str(request.metadata.get("empirical_optimize","cost_per_quality"))
        perf_rows={p.model_id:p for p in self.ledger.performance(task_class)}
        eligible=[mid for mid in static.eligible]
        perf_payload={mid:perf_rows[mid].to_dict() for mid in eligible if mid in perf_rows}

        if explore:
            under=[mid for mid in eligible if perf_rows.get(mid) is None or perf_rows[mid].samples<min_samples]
            if under:
                profile_map={p.model_id:p for p in profiles}
                chosen=sorted(under,key=lambda mid:(perf_rows[mid].samples if mid in perf_rows else 0,profile_map[mid].cost_per_1k_output,-profile_map[mid].strength,mid))[0]
                profile=profile_map[chosen]
                return AdaptiveRouteResult(request.task_id,chosen,profile.provider,None,eligible,static.rejected,"deterministic calibration of under-sampled eligible model",task_class,True,perf_payload,static.selected_model_id)

        qualified=[]
        for mid in eligible:
            perf=perf_rows.get(mid)
            if perf is None or perf.samples<min_samples: continue
            if perf.acceptance_lower_bound+1e-12<acceptance_floor: continue
            qualified.append(mid)
        if not qualified:
            return AdaptiveRouteResult(**asdict(static),task_class=task_class,adaptive=False,performance=perf_payload,static_selected_model_id=static.selected_model_id)

        profile_map={p.model_id:p for p in profiles}
        if optimize_empirical=="quality":
            key=lambda mid:(-perf_rows[mid].acceptance_lower_bound,perf_rows[mid].repair_rate,profile_map[mid].cost_per_1k_output,mid)
        elif optimize_empirical=="latency":
            key=lambda mid:((perf_rows[mid].avg_latency_seconds if perf_rows[mid].avg_latency_seconds is not None else float("inf")),-perf_rows[mid].acceptance_lower_bound,mid)
        else:
            key=lambda mid:(-self._cost_efficiency(perf_rows[mid]),perf_rows[mid].repair_rate,profile_map[mid].cost_per_1k_output,mid)
        chosen=sorted(qualified,key=key)[0]; profile=profile_map[chosen]; perf=perf_rows[chosen]
        return AdaptiveRouteResult(request.task_id,chosen,profile.provider,perf.acceptance_lower_bound,eligible,static.rejected,f"adaptive {optimize_empirical} route from explicit evaluated outcomes",task_class,True,perf_payload,static.selected_model_id)
