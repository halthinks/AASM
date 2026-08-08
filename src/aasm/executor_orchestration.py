from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .economics import CallPurpose, ModelUsageRecord
from .model_routing import ModelRouteRequest


class ExecutorAdapter(Protocol):
    def run(self, prompt: str, **kwargs): ...


@dataclass
class ExecutorBinding:
    """Worker-local binding from AASM routing decisions to a physical executor."""

    executor_id: str
    adapter: ExecutorAdapter
    providers: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.executor_id:
            raise ValueError("executor_id is required")
        self.providers = sorted(set(self.providers))
        self.capabilities = sorted(set(self.capabilities))

    def supports(self, provider: str | None, required: list[str]) -> bool:
        if not self.enabled:
            return False
        if self.providers and provider not in self.providers:
            return False
        return set(required).issubset(set(self.capabilities))


@dataclass
class ExecutionContract:
    """Normalized execution intent embedded in a task lease's metadata."""

    prompt: str
    purpose: str = CallPurpose.PRODUCTIVE.value
    instructions: str | None = None
    reasoning_effort: str | None = None
    executor_id: str | None = None
    fixed_model_id: str | None = None
    model_required_capabilities: list[str] = field(default_factory=list)
    executor_required_capabilities: list[str] = field(default_factory=list)
    min_strength: float = 0.0
    min_context_window: int = 0
    max_cost_per_1k_output: float | None = None
    optimize: str = "balanced"
    candidate_model_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.prompt:
            raise ValueError("execution prompt is required")
        self.model_required_capabilities = sorted(set(self.model_required_capabilities))
        self.executor_required_capabilities = sorted(set(self.executor_required_capabilities))

    @classmethod
    def from_lease(cls, lease: dict[str, Any]) -> "ExecutionContract":
        metadata = dict(lease.get("metadata") or {})
        raw = dict(metadata.get("execution") or {})
        if "prompt" not in raw and metadata.get("prompt"):
            raw["prompt"] = metadata["prompt"]
        if "purpose" not in raw and metadata.get("purpose"):
            raw["purpose"] = metadata["purpose"]
        return cls(**raw)


@dataclass
class OrchestrationResult:
    task_id: str
    lease_id: str
    executor_id: str
    model_id: str | None
    provider: str | None
    output_text: str
    usage: dict[str, Any]
    route: dict[str, Any] | None = None
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class ExecutorRegistry:
    def __init__(self):
        self._bindings: dict[str, ExecutorBinding] = {}

    def register(self, binding: ExecutorBinding):
        if binding.executor_id in self._bindings:
            raise ValueError(f"Executor already registered: {binding.executor_id}")
        self._bindings[binding.executor_id] = binding
        return binding

    def get(self, executor_id: str):
        try:
            return self._bindings[executor_id]
        except KeyError as exc:
            raise KeyError(f"Unknown executor: {executor_id}") from exc

    def select(self, *, provider: str | None, required_capabilities: list[str], executor_id: str | None = None):
        if executor_id:
            binding = self.get(executor_id)
            if not binding.supports(provider, required_capabilities):
                raise ValueError(f"Executor {executor_id} cannot satisfy provider/capability contract")
            return binding
        eligible = [b for b in self._bindings.values() if b.supports(provider, required_capabilities)]
        if not eligible:
            raise ValueError(f"No executor satisfies provider={provider!r} capabilities={sorted(required_capabilities)!r}")
        return sorted(eligible, key=lambda b: (-b.priority, b.executor_id))[0]

    def describe(self):
        return [
            {
                "executor_id": b.executor_id,
                "providers": list(b.providers),
                "capabilities": list(b.capabilities),
                "enabled": b.enabled,
                "priority": b.priority,
                "metadata": dict(b.metadata),
            }
            for b in sorted(self._bindings.values(), key=lambda x: x.executor_id)
        ]


class ExecutionOrchestrator:
    """Turn a claimed lease into a real routed model/executor invocation."""

    def __init__(self, client, machine_id: str, registry: ExecutorRegistry):
        self.client = client
        self.machine_id = machine_id
        self.registry = registry

    @staticmethod
    def _usage_dict(usage: ModelUsageRecord | dict[str, Any] | None, *, task_id: str, executor_id: str):
        if usage is None:
            return asdict(ModelUsageRecord("unreported", CallPurpose.PRODUCTIVE.value, task_id=task_id, metadata={"executor": executor_id, "unreported": True}))
        raw = asdict(usage) if isinstance(usage, ModelUsageRecord) else dict(usage)
        raw.setdefault("task_id", task_id)
        metadata = dict(raw.get("metadata") or {})
        metadata.setdefault("executor", executor_id)
        raw["metadata"] = metadata
        return raw

    def _route(self, task_id: str, contract: ExecutionContract):
        if contract.fixed_model_id:
            state = self.client.state(self.machine_id)
            profiles = {m.get("model_id"): m for m in state.get("models", [])}
            profile = profiles.get(contract.fixed_model_id)
            if profile is None:
                raise ValueError(f"Fixed model is not registered: {contract.fixed_model_id}")
            return {
                "task_id": task_id,
                "selected_model_id": contract.fixed_model_id,
                "provider": profile.get("provider"),
                "reason": "fixed model requested by execution contract",
                "eligible": [contract.fixed_model_id],
                "rejected": {},
                "score": None,
            }
        request = ModelRouteRequest(
            task_id=task_id,
            required_capabilities=contract.model_required_capabilities,
            min_strength=contract.min_strength,
            min_context_window=contract.min_context_window,
            max_cost_per_1k_output=contract.max_cost_per_1k_output,
            optimize=contract.optimize,
            candidate_ids=contract.candidate_model_ids,
            metadata=dict(contract.metadata),
        )
        route = self.client.route_model(self.machine_id, request)
        if not route.get("selected_model_id"):
            raise ValueError(route.get("reason") or "No eligible model")
        return route

    def execute(self, lease: dict[str, Any]):
        task_id = str(lease["task_id"])
        lease_id = str(lease["lease_id"])
        contract = ExecutionContract.from_lease(lease)
        route = self._route(task_id, contract)
        model_id = route.get("selected_model_id")
        provider = route.get("provider")
        binding = self.registry.select(
            provider=provider,
            required_capabilities=contract.executor_required_capabilities,
            executor_id=contract.executor_id,
        )

        kwargs: dict[str, Any] = {
            "model": model_id,
            "purpose": contract.purpose,
            "task_id": task_id,
        }
        if contract.instructions is not None:
            kwargs["instructions"] = contract.instructions
        if contract.reasoning_effort is not None:
            kwargs["reasoning_effort"] = contract.reasoning_effort

        # Adapters intentionally have slightly different optional keyword surfaces.
        # Remove unsupported optional fields only when the adapter reports them.
        try:
            result = binding.adapter.run(contract.prompt, **kwargs)
        except TypeError as exc:
            if "instructions" not in str(exc) and "reasoning_effort" not in str(exc):
                raise
            kwargs.pop("instructions", None)
            kwargs.pop("reasoning_effort", None)
            result = binding.adapter.run(contract.prompt, **kwargs)

        output_text = str(getattr(result, "output_text", "") or "")
        usage = self._usage_dict(getattr(result, "usage", None), task_id=task_id, executor_id=binding.executor_id)
        if hasattr(self.client, "model_usage"):
            self.client.model_usage(self.machine_id, usage)

        evidence = []
        response_id = getattr(result, "response_id", None)
        thread_id = getattr(result, "thread_id", None)
        if response_id:
            evidence.append(f"openai_response:{response_id}")
        if thread_id:
            evidence.append(f"codex_thread:{thread_id}")

        return OrchestrationResult(
            task_id=task_id,
            lease_id=lease_id,
            executor_id=binding.executor_id,
            model_id=model_id,
            provider=provider,
            output_text=output_text,
            usage=usage,
            route=route,
            evidence=evidence,
            metadata={"execution_contract": asdict(contract)},
        ).to_dict()
