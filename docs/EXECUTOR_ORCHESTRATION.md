# Executor orchestration

AASM v0.10 closes the gap between scheduling work and physically executing it.

A scheduled task can now carry an `execution` contract in `TaskDemand.metadata`. A remote worker claims the resulting lease, routes the task to a registered model, selects a compatible worker-local executor, invokes the real adapter, records model usage, and completes or fails the lease.

## Execution path

```text
TaskDemand
   ↓
schedule / lease
   ↓
ExecutionContract
   ↓
ModelStrengthRouter
   ↓
ExecutorRegistry
   ↓
CodexCLIExecutor | OpenAIResponsesExecutor | custom adapter
   ↓
usage + output + evidence
   ↓
durable lease completion
```

## Task contract

```json
{
  "task_id": "implement-api",
  "required_capabilities": ["code"],
  "metadata": {
    "execution": {
      "prompt": "Implement the API endpoint and run its tests.",
      "purpose": "productive",
      "model_required_capabilities": ["code"],
      "executor_required_capabilities": ["code"],
      "min_strength": 0.7,
      "optimize": "balanced"
    }
  }
}
```

`fixed_model_id` can pin a task to a registered model. Otherwise the normal durable model router chooses a model using capability, strength, context, cost and optimization constraints.

`executor_id` can pin the physical execution adapter. Otherwise `ExecutorRegistry` selects the highest-priority enabled executor compatible with the selected model provider and requested executor capabilities.

## Real worker process

Start the control plane first, then run a worker on any reachable machine:

```bash
aasm worker \
  --url https://aasm.example \
  --machine-id MACHINE_ID \
  --worker-id coding-01 \
  --resource-id coding-pool \
  --executor codex \
  --executor-id codex-cli \
  --provider openai \
  --capability code \
  --cwd /workspace/repository \
  --token "$AASM_SERVER_TOKEN"
```

For a Responses API worker use `--executor responses`; `OPENAI_API_KEY` must be available to that worker process.

`--once` performs one claim/execution cycle and exits, which is useful for debugging and batch/container jobs.

## Restart semantics

A worker restart with the same `worker_id` reconnects to the existing durable worker when its resource binding matches. A changed resource binding is rejected instead of silently moving ownership.

## Usage and provenance

When an adapter returns `ModelUsageRecord`, the worker reports it through `/model-usage` before completing the lease. The durable completion result records:

- selected model and provider;
- selected executor;
- normalized output text;
- token-usage payload;
- routing decision;
- provider response/thread evidence IDs when exposed by the adapter;
- the execution contract that produced the invocation.

This is the foundation for adaptive model routing: v0.10 captures the execution/outcome data that later routing versions can learn from.

## Boundary

A task lease grants ownership of work; it is not itself authorization for arbitrary external side effects. Operations that need AASM's external-effect guarantees still use `EffectSpec`, idempotency and effect reconciliation.
