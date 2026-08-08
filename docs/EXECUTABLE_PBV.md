# Executable Planner / Builder / Verifier orchestration

AASM v0.13 turns the Planner / Builder / Verifier pattern into a durable runtime profile rather than a prompt convention.

## Authority model

The profile has one hard invariant:

> **Only the registered Planner owns the authoritative plan.**

Builders execute assigned work. Verifiers inspect Builder output and may recommend a control response. Neither role can mutate the plan or authorize continuation.

The Planner commits one of exactly five directives:

- `CONTINUE`
- `REPAIR`
- `INVESTIGATE`
- `PAUSE`
- `PLAN_INTERRUPT`

A `PLAN_INTERRUPT` is the only directive allowed to mutate the plan and it must carry an explicit `plan_patch`. The patch is applied to a copy of the current graph, validated for legal nodes/edges and acyclicity, and only then committed atomically with the new plan revision.

## Runtime records

`TeamMember` declares a durable team member and role.

`BuilderOutput` records the Builder's observed work, test output, changed files, assumptions, and evidence.

`VerifierReport` records verification findings plus a recommendation. AASM also calculates a deterministic `policy_recommendation` from blocking state, assumption changes, unexpected output, tests, and acceptance. The Verifier recommendation remains advisory.

`PlannerDecision` is the authoritative control message and records the Planner, task, directive, reason, source Verifier report, plan revision before/after, optional plan patch, and metadata.

## Automatic handoff

`PBVCoordinator` implements the physical handoff:

```text
Builder output
    ↓
AASM persists BuilderOutput
    ↓
Verifier callable / agent / service
    ↓
AASM persists VerifierReport
    ↓
Planner callable / agent / service
    ↓
AASM validates Planner authority
    ↓
PlannerDecision committed
    ↓
CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT
```

The Verifier and Planner callables may be backed by OpenAI Responses, Codex, another provider, a remote service, a human approval surface, or deterministic test code. Their implementation is deliberately transport-neutral.

## Plan interrupt semantics

A `PLAN_INTERRUPT` exists for changed assumptions, unexpected output, or another event that invalidates part of the current plan. It is not inferred as a hidden rewrite.

Example patch:

```json
{
  "add_nodes": [
    {"node_id":"repair-parser","kind":"repair","payload":{"reason":"new parser constraint"}}
  ],
  "add_edges": [
    {"src":"repair-parser","dst":"integration-test","relation":"requires"}
  ],
  "update_nodes": [
    {"node_id":"old-task","status":"blocked"}
  ],
  "prune_nodes": ["obsolete-path"]
}
```

A cyclic or otherwise invalid patch raises an error and leaves the authoritative graph and plan revision unchanged.

## Remote use

The control plane exposes:

- `GET /v1/machines/{machine_id}/team`
- `POST /v1/machines/{machine_id}/team/initialize`
- `POST /v1/machines/{machine_id}/team/builder-output`
- `POST /v1/machines/{machine_id}/team/verifier-report`
- `POST /v1/machines/{machine_id}/team/planner-decision`

`AASMRemoteClient` exposes matching helpers.

## CLI

```bash
aasm team MACHINE_ID --store runs.db
aasm team-init MACHINE_ID --store runs.db --members members.json
aasm builder-output MACHINE_ID --store runs.db --record builder.json
aasm verifier-report MACHINE_ID --store runs.db --record verifier.json
aasm planner-decision MACHINE_ID --store runs.db --record decision.json
```

## Important boundary

This profile does not make Planner/Builder the AASM core architecture. It is one executable orchestration profile built on the same role-agnostic state, resource, lease, model-routing, governance, and evidence infrastructure used by other topologies.
