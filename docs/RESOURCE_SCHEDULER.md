# Durable Capability Registry and Resource Scheduler

AASM v0.6 makes agents, tools, humans, services, and constrained execution slots first-class durable resources.

## Resource records

A `ResourceRecord` declares:

- `resource_id`
- `kind` such as `agent`, `tool`, `human`, `service`, or `gpu`
- capability strings
- available capacity
- cost per unit
- reliability score
- enabled/disabled state
- arbitrary metadata

Registration and updates are event-sourced into the machine snapshot, so the resource view survives restart, replay, and forks.

## Task demand

A `TaskDemand` can constrain scheduling by:

- required capabilities
- demand amount
- priority
- allowed resource kinds
- maximum cost per unit
- minimum reliability

## Scheduling algorithm

AASM builds a bipartite flow network:

`source → task demand → eligible resources → sink`

The existing Edmonds-Karp engine computes maximum feasible allocation and the minimum cut. The scheduler records assignments, unmet demand, utilization, and bottlenecks as durable state.

Tasks are inserted in descending priority order so capacity-constrained flow resolves deterministically in favor of higher-priority work.

## Bottlenecks

When resource capacity is the limiting cut, AASM reports the resource IDs in the bottleneck set. When no resource satisfies a task's required capabilities, it reports `capability:<task_id>` rather than inventing a resource.

## Planning integration

If a scheduled `task_id` matches a durable plan-node ID, AASM writes the selected resource into that node's `owner` field. This ties the execution graph to the scheduler without making the planner itself role-specific.

## CLI

Inspect the durable registry and last schedule:

```bash
aasm resources MACHINE_ID --db runs.db
```

Compute a new schedule from a JSON list of task-demand objects:

```bash
aasm schedule MACHINE_ID --db runs.db --tasks tasks.json
```

## Fork semantics

Historical forks receive exactly the resource registry and schedule state visible at the fork event boundary. Resources or assignments created later in the source run do not leak into the fork.
