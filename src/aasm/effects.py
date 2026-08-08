from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from .model import new_id, now


class EffectStatus(str, Enum):
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    retry_on_failure: bool = False
    retry_on_unknown: bool = False


@dataclass
class EffectSpec:
    effect_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    preconditions: list[dict[str, Any]] = field(default_factory=list)
    postconditions: list[dict[str, Any]] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    reversible: bool = False
    compensation: dict[str, Any] | None = None
    effect_id: str = field(default_factory=lambda: new_id("effect"))

    def __post_init__(self):
        if not self.idempotency_key:
            self.idempotency_key = self.effect_id


@dataclass
class EffectRecord:
    machine_id: str
    spec: EffectSpec
    status: str = EffectStatus.PROPOSED.value
    attempts: int = 0
    authorization_id: str | None = None
    authority: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    evidence: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)


class EffectExecutor(Protocol):
    """Executor contract.

    The same idempotency_key is supplied on every retry. Executors that can
    provide strong exactly-once behavior should deduplicate by that key.
    """

    def __call__(self, spec: EffectSpec, idempotency_key: str) -> dict[str, Any]: ...


class EffectExecutionError(RuntimeError):
    pass


class EffectUnknownOutcome(RuntimeError):
    """Raised when a prior RUNNING attempt may have reached the external system.

    Retrying automatically could duplicate the side effect. Reconcile first or
    explicitly configure a retry-safe executor/policy.
    """
