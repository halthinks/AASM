from dataclasses import asdict, dataclass

@dataclass(frozen=True)
class ReuseMetrics:
    attempts:int=0
    exact_hits:int=0
    subsumption_hits:int=0
    negative_prunes:int=0
    stale_rejections:int=0
    privacy_rejections:int=0
    freshness_rejections:int=0
    environment_rejections:int=0
    model_calls_avoided:int=0
    tool_calls_avoided:int=0
    solver_runs_avoided:int=0
    input_units_avoided:int=0
    output_units_avoided:int=0
    def to_dict(self): return asdict(self)
