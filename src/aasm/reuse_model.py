from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .semantic_result import semantic_fingerprint

REUSE_CONTRACT_ID = "aasm.reuse.v1"
REUSE_CONTRACT_VERSION = "0.1.0"
REUSE_CERTIFICATE_CONTRACT_ID = "aasm.reuse.certificate.v1"
REUSE_CERTIFICATE_CONTRACT_VERSION = "0.1.0"
REUSE_MODES = {"EXACT", "IDEMPOTENT", "SUBSUMES", "CERTIFIED_EQUIVALENT"}
REUSE_EFFECT_CLASSES = {"PURE", "READ_ONLY_FRESHNESS_BOUND", "IDEMPOTENT_WRITE", "NON_IDEMPOTENT_EFFECT"}
REUSE_KINDS = {
    "COMPILER_RESULT", "FORMAL_VERIFICATION_RESULT", "TOOL_OBSERVATION",
    "CONTEXT_PROJECTION", "CAPABILITY_RESULT", "SUBPROBLEM_RESULT",
    "PARTIAL_RESULT", "NEGATIVE_RESULT", "PROOF", "EMBEDDING_INDEX", "LLM_RESULT",
}


def reuse_contract() -> dict[str, Any]:
    return {
        "contract_id": REUSE_CONTRACT_ID,
        "contract_version": REUSE_CONTRACT_VERSION,
        "certificate_contract_id": REUSE_CERTIFICATE_CONTRACT_ID,
        "certificate_contract_version": REUSE_CERTIFICATE_CONTRACT_VERSION,
        "authority": "INDEX_AND_VALIDATE_ONLY",
        "canonical_state": "REFERENCES_EXISTING_AASM_OBJECTS",
        "cache_deletion_semantics": "PERFORMANCE_ONLY",
        "similarity_semantics": "CANDIDATE_DISCOVERY_ONLY",
        "subsumption_semantics": "EXPLICIT_VALIDATOR_REQUIRED",
        "dependency_invalidation": "V38_SEMANTIC_DEPENDENCY_SIGNALS",
        "privacy_boundary": "V40_SCOPE_AND_PRINCIPAL",
    }


@dataclass(frozen=True)
class CanonicalRef:
    ref_type: str
    ref_id: str
    fingerprint: str
    scope_id: str = "root"
    privacy_level: str = "PUBLIC"
    privacy_principal_id: str = ""

    def __post_init__(self):
        if not self.ref_type or not self.ref_id or not self.fingerprint:
            raise ValueError("canonical ref requires ref_type, ref_id, and fingerprint")
        if self.privacy_level not in {"AGENT", "USER", "SHARED", "PUBLIC"}:
            raise ValueError("invalid privacy level")
        if self.privacy_level in {"AGENT", "USER"} and not self.privacy_principal_id:
            raise ValueError("private canonical ref requires privacy_principal_id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReuseRequest:
    kind: str
    semantic_payload: Any
    scope_id: str = "root"
    privacy_level: str = "PUBLIC"
    privacy_principal_id: str = ""
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    freshness_seconds: float | None = None
    as_of: float | None = None
    effect_class: str = "PURE"
    required_strength: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in REUSE_KINDS:
            raise ValueError(f"invalid reuse kind: {self.kind}")
        if self.effect_class not in REUSE_EFFECT_CLASSES:
            raise ValueError(f"invalid reuse effect class: {self.effect_class}")
        if self.privacy_level in {"AGENT", "USER"} and not self.privacy_principal_id:
            raise ValueError("private reuse request requires privacy_principal_id")
        if self.freshness_seconds is not None and self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({
            "kind": self.kind,
            "semantic_payload": deepcopy(self.semantic_payload),
            "scope_id": self.scope_id,
            "privacy_level": self.privacy_level,
            "privacy_principal_id": self.privacy_principal_id,
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": sorted(set(self.dependency_fingerprints)),
            "effect_class": self.effect_class,
            "required_strength": self.required_strength,
            "metadata": deepcopy(self.metadata),
        })

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class ReuseCandidate:
    kind: str
    request_fingerprint: str
    source: CanonicalRef
    semantic_payload: Any
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    created_at: float | None = None
    effect_class: str = "PURE"
    verification_strength: str = ""
    reusable_modes: tuple[str, ...] = ("EXACT",)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in REUSE_KINDS:
            raise ValueError(f"invalid reuse kind: {self.kind}")
        if self.effect_class not in REUSE_EFFECT_CLASSES:
            raise ValueError("invalid reuse effect class")
        if set(self.reusable_modes) - REUSE_MODES:
            raise ValueError("invalid reusable mode")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({
            "kind": self.kind,
            "request_fingerprint": self.request_fingerprint,
            "source": self.source.to_dict(),
            "semantic_payload": deepcopy(self.semantic_payload),
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": sorted(set(self.dependency_fingerprints)),
            "created_at": self.created_at,
            "effect_class": self.effect_class,
            "verification_strength": self.verification_strength,
            "reusable_modes": sorted(set(self.reusable_modes)),
            "metadata": deepcopy(self.metadata),
        })

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "source": self.source.to_dict(), "fingerprint": self.fingerprint}
