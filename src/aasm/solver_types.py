from dataclasses import dataclass,field

@dataclass(frozen=True)
class SolverStepRequest:
    scope_id:str="root"
    objective_id:str=""
    obligation_id:str=""
    capability_id:str=""
    metadata:dict=field(default_factory=dict)

@dataclass(frozen=True)
class SolverStepResult:
    request_fingerprint:str
    phase:str
    status:str
    action:str
    selected_obligation_id:str=""
    reuse_certificate_id:str=""
    details:dict=field(default_factory=dict)
