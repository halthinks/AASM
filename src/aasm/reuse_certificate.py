from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
from .reuse_model import CanonicalRef, REUSE_MODES

@dataclass(frozen=True)
class ReuseValidation:
    usable: bool
    mode: str | None
    reasons: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    validator_id: str = "aasm.reuse.validator"
    validator_version: str = "0.1.0"
    def __post_init__(self):
        if self.mode is not None and self.mode not in REUSE_MODES:
            raise ValueError("invalid reuse mode")
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ReuseCertificate:
    request_fingerprint: str
    source: CanonicalRef
    source_candidate_fingerprint: str
    equivalence_mode: str
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    scope_id: str = "root"
    privacy_principal_id: str = ""
    verifier_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    valid: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    certificate_id: str = ""
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
