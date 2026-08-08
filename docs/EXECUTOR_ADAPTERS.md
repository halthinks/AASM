# Executor adapters

AASM is a control plane. A worker becomes an AI worker only when it is attached to a real executor.

v0.9 includes two concrete adapters.

## OpenAI Responses API

`OpenAIResponsesExecutor` sends a real Responses API request to an explicitly selected model and returns both output and token usage.

```python
from aasm import OpenAIResponsesExecutor

executor = OpenAIResponsesExecutor()
result = executor.run(
    "Inspect this proposed migration and identify blocking risks.",
    model="gpt-5.6-sol",
    purpose="verification",
    reasoning_effort="high",
    task_id="review-42",
)
engine.record_model_usage(result.usage)
```

The adapter extracts cached-input usage when the provider reports it so AASM economics can distinguish cached from fresh context.

## Codex CLI

`CodexCLIExecutor` wraps headless `codex exec --json` without changing Codex permission posture.

```python
from aasm import CodexCLIExecutor

executor = CodexCLIExecutor(cwd="/srv/worktrees/task-17")
result = executor.run(
    "Implement the assigned task and run its tests.",
    model="gpt-5.6-terra",
    task_id="task-17",
)
engine.record_model_usage(result.usage)
```

The executor intentionally does not enable unsafe flags. Sandbox mode, approval policy, network policy, and managed Codex rules remain separately configured controls.

## Physical multi-agent execution

An AASM deployment can therefore have many remote workers, each with a different executor:

```text
Postgres + AASM control plane
        |
        +-- worker-us-1  -> Codex CLI / Terra
        +-- worker-us-2  -> Responses API / Luna
        +-- worker-eu-1  -> Responses API / Sol
        +-- worker-gpu-1 -> local simulation tool
        +-- worker-human -> approval queue
```

Each worker still obeys the same durable task lease protocol. Model selection is a resource-routing decision, not an implicit property of the worker.

## Massive collaboration

Scale comes from adding independently leased work units and execution endpoints, not from pretending one conversation contains many physical agents. AASM can coordinate hundreds of logical tasks as long as the backing database, worker fleet, provider rate limits, and budgets support the desired concurrency.

The scheduler should use min-cut/bottleneck evidence before adding workers. Model routing should use strength/cost/latency constraints before selecting expensive models. Governance accounting should prevent review overhead from silently dominating productive work.
