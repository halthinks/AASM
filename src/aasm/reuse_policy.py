from dataclasses import dataclass

@dataclass(frozen=True)
class ReusePolicy:
    allow_exact:bool=True
    allow_idempotent:bool=True
    allow_subsumption:bool=True
    allow_certified_equivalent:bool=True
