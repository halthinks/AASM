# Massive collaboration scheduler

AASM v0.14 decides how much parallelism is actually useful before a fleet is expanded.

The collaboration planner combines:

- dependency-graph critical path
- topological execution waves and maximum parallel width
- total estimated work
- capability-aware max-flow scheduling
- eligible resource capacity rather than raw fleet size
- min-cut bottlenecks
- resource cost proxy
- configurable coordination overhead
- minimum useful marginal improvement

The goal is not to maximize worker count. It is to minimize projected completion time while using the smallest team that is effectively near-optimal.

## Model

For candidate worker count `n`, AASM computes a lower-bound-style projection:

`projected_makespan(n) = max(critical_path, total_work / n) + coordination_overhead(n)`

The candidate set is capped by all of:

1. configured `max_workers`
2. number of runnable tasks
3. maximum parallel DAG width
4. physical enabled resource capacity
5. capability-eligible max-flow capacity

AASM therefore refuses to recommend 100 workers for a serial chain, and it refuses to count workers that cannot satisfy the required capabilities.

## Policy

```python
from aasm import CollaborationPolicy

policy = CollaborationPolicy(
    max_workers=128,
    coordination_overhead_per_extra_worker=0.05,
    min_relative_improvement=0.02,
    near_optimal_tolerance=0.02,
)
```

`near_optimal_tolerance` lets AASM choose a smaller team when its projected makespan is effectively indistinguishable from the mathematical best candidate. `min_relative_improvement` prevents adding another worker for negligible marginal gain.

## Durable analysis

```python
analysis = engine.analyze_collaboration(policy=policy)
print(analysis["recommended_workers"])
print(analysis["bottlenecks"])
```

The result is persisted under the machine resource state and appears in the Control Center.

## CLI

```bash
aasm collaboration MACHINE_ID --store runs.db --policy collaboration-policy.json
```

Pass `--tasks tasks.json` to analyze an explicit task set. If omitted, AASM uses the most recently scheduled durable tasks.

## Remote API

`POST /v1/machines/{machine_id}/collaboration/analyze`

The request can contain `policy` and optional `tasks`. The last analysis is available at:

`GET /v1/machines/{machine_id}/collaboration`

## What this does not do

v0.14 recommends useful concurrency; it does not invent workers or silently provision infrastructure. Worker creation remains an explicit deployment/executor concern. The recommendation is evidence for the Planner or operator.

AASM also does not assume that more model instances imply more independent useful work. Dependency width and capability/min-cut evidence remain hard structural limits.
