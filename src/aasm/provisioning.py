from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Protocol

from .model import new_id


class ProvisioningAction:
    PROVISION = "PROVISION"
    DRAIN = "DRAIN"
    ALL = {PROVISION, DRAIN}


@dataclass
class ProvisioningRequest:
    provider: str
    resource_id: str
    action: str
    count: int
    reason: str
    target_worker_ids: list[str] = field(default_factory=list)
    request_id: str = field(default_factory=lambda: new_id("provision"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.provider or not self.resource_id or not self.reason:
            raise ValueError("provider, resource_id, and reason are required")
        if self.action not in ProvisioningAction.ALL:
            raise ValueError(f"invalid provisioning action: {self.action}")
        if self.count < 1:
            raise ValueError("count must be positive")
        self.target_worker_ids = sorted(set(self.target_worker_ids))
        if self.action == ProvisioningAction.DRAIN and self.target_worker_ids and len(self.target_worker_ids) > self.count:
            raise ValueError("target_worker_ids cannot exceed drain count")

    def to_dict(self):
        return asdict(self)


@dataclass
class ProvisioningPlan:
    desired_workers: int
    current_workers: int
    delta: int
    requests: list[ProvisioningRequest] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "desired_workers": self.desired_workers,
            "current_workers": self.current_workers,
            "delta": self.delta,
            "requests": [x.to_dict() for x in self.requests],
            "metadata": dict(self.metadata),
        }


class ProvisioningAdapter(Protocol):
    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict[str, Any]: ...


class FunctionProvisioningAdapter:
    def __init__(self, fn: Callable[[ProvisioningRequest, str], dict[str, Any]]):
        self.fn = fn

    def apply(self, request: ProvisioningRequest, idempotency_key: str):
        return dict(self.fn(request, idempotency_key) or {})


class ProvisioningRegistry:
    def __init__(self):
        self._adapters: dict[str, ProvisioningAdapter] = {}

    def register(self, provider: str, adapter: ProvisioningAdapter):
        if not provider:
            raise ValueError("provider is required")
        if provider in self._adapters:
            raise ValueError(f"Provisioning provider already registered: {provider}")
        self._adapters[provider] = adapter
        return adapter

    def get(self, provider: str):
        if provider not in self._adapters:
            raise KeyError(f"Unknown provisioning provider: {provider}")
        return self._adapters[provider]

    def providers(self):
        return sorted(self._adapters)
