"""Minimal in-process example of AASM v0.10 executor orchestration.

For real multi-host use, run `aasm serve` and `aasm worker` on separate hosts.
"""

from dataclasses import dataclass

from aasm import (
    ExecutorBinding,
    ExecutorRegistry,
    ExecutionOrchestrator,
    ModelUsageRecord,
)


@dataclass
class DemoResult:
    output_text: str
    usage: ModelUsageRecord
    response_id: str = "demo-response"


class DemoAdapter:
    def run(self, prompt, *, model=None, purpose="productive", task_id=None, **kwargs):
        return DemoResult(
            output_text=f"{model}: {prompt}",
            usage=ModelUsageRecord(model or "demo", purpose, input_tokens=25, output_tokens=10, task_id=task_id),
        )


class DemoClient:
    def route_model(self, machine_id, request):
        return {
            "task_id": request.task_id,
            "selected_model_id": "terra",
            "provider": "openai",
            "score": 1.0,
            "eligible": ["terra"],
            "rejected": {},
            "reason": "demo route",
        }

    def model_usage(self, machine_id, record):
        print("usage:", record)

    def state(self, machine_id):
        return {"models": [{"model_id": "terra", "provider": "openai"}]}


registry = ExecutorRegistry()
registry.register(ExecutorBinding("demo", DemoAdapter(), providers=["openai"], capabilities=["code"]))
orchestrator = ExecutionOrchestrator(DemoClient(), "machine-demo", registry)

print(orchestrator.execute({
    "task_id": "task-demo",
    "lease_id": "lease-demo",
    "metadata": {
        "execution": {
            "prompt": "Implement the requested function.",
            "model_required_capabilities": [],
            "executor_required_capabilities": ["code"],
        }
    },
}))
