---
name: aasm-algorithmic-agent-state-machine
description: Use AASM to structure multi-step AI work as a durable algorithmic state machine with explicit transitions, graph planning, recovery, evidence, resource/model routing, authority, distributed workers, mission controls, and observable execution.
---

# AASM Skill

## When to use

Use AASM for work that is multi-step, branchy, stateful, expensive to repeat, distributed, dependent on scarce tools/models, requires auditable plan changes, or must recover deterministically after failure.

AASM is role-agnostic. Do not assume Planner/Builder unless that profile is intentionally selected.

## Core operating rules

1. Formalize the objective, constraints, invariants, acceptance tests, and structural features.
2. Instantiate `AASMEngine(ProblemSpec(...))`; use `SQLiteStore` or `PostgresStore` for recoverable work.
3. Move only through legal transitions. Never mutate snapshot fields directly.
4. Represent nontrivial dependencies as a durable `PlanGraph`.
5. Checkpoint before risky branching, irreversible decisions, or assumption-sensitive work.
6. Use durable DP memory only within an explicit validity scope; invalidate it when assumptions change.
7. Register constrained agents, tools, model slots, GPUs, API quotas, or human reviewers as resources; schedule with capability/capacity evidence.
8. Inspect min-cut and critical-path evidence before adding workers.
9. Separate capability from authority. A worker may produce output without permission to redefine the plan or execute an external effect.
10. Record evidence and provenance for every material transition, claim, assumption, contradiction, and external action.
11. Treat verification as evidence, not authority. Resolve blocking findings before commitment.
12. Complete only when acceptance tests are satisfied; terminal failure must state why.

## Durable effects

Represent externally visible actions as `EffectSpec` records. Persist the intent before execution, authorize it explicitly, and execute through the effect boundary.

- Reuse stable idempotency keys for semantically identical operations.
- Never blindly retry `UNKNOWN` outcomes.
- Reconcile external state before retry unless the executor is explicitly safe.
- Passive resume must not reclassify healthy remote `RUNNING` attempts.
- SQLite/PostgreSQL atomically claim attempts; finalization must retain the execution ownership token.
- Effect approval does not execute the effect.

## Durable planning, memory, and evidence

Use engine-level durable APIs such as:

```text
plan_add_node / plan_add_edge / plan_update_node
plan_mark_visited / plan_prune_node
memo_put / memo_get / memo_invalidate
add_claim / add_observation / add_assumption / add_contradiction
invalidate_evidence / evidence_lineage
```

Do not bypass them with direct object mutation when the state must survive restart, replay, or fork.

## Distributed workers

When multiple processes or hosts can execute work:

- register workers against durable resources;
- claim tasks through `claim_task()` / `claim_next_task()`;
- heartbeat workers and long-running leases;
- enforce machine, worker, and resource quotas;
- expire/reclaim abandoned leases;
- use PostgreSQL for real multi-host coordination;
- resume from canonical durable state after another host advances the machine.

A lease grants task ownership. It does not authorize externally visible side effects.

## Model routing and executor orchestration

Treat model choice as resource routing when model classes differ in capability, strength, context, latency, cost, or concurrency.

- Register `ModelProfile` records.
- Use `ModelRouteRequest` with hard capability/quality/context/cost floors.
- Never allow empirical history to weaken static eligibility.
- Route a claimed task through:

```text
lease
→ execution contract
→ model route
→ executor selection
→ provider/Codex invocation
→ usage and evidence
→ durable completion/failure
```

A model route is not proof that an executable provider adapter exists.

## Adaptive model routing

Learn from **explicit evaluated outcomes**, not merely non-error API responses.

Record `ModelOutcomeRecord` after verification with task class, model, accepted/rejected status, repair requirement, score, latency, cost, executor, and provenance.

- Use Wilson lower bounds for conservative acceptance evidence.
- Keep task classes narrow and comparable.
- Fall back to deterministic static routing when evidence is insufficient.
- Explore under-sampled models only when deliberate calibration is enabled.
- Prefer the least-cost model with demonstrated quality when using cost-per-quality routing.

## Model and governance economics

Record productive, verification, governance, permission-review, synthesis, and retry calls separately, including cached reads and explicit cache writes when available.

Use deterministic policy for routine benign permission decisions. Spend model reasoning when information, assumptions, evidence, risk, or scope materially changes.

Governance optimization controls whether another semantic review is needed. It does **not** authorize execution or weaken sandbox, network, credential, effect, or destructive-operation boundaries.

Hard governance-budget exhaustion must pause required review, never waive it.

## Executable Planner / Builder / Verifier

When the PBV profile is selected:

- exactly one enabled Planner owns authoritative plan mutation;
- Builders submit outputs, artifacts, diffs, tests, assumptions, and evidence;
- Verifiers inspect and recommend but do not authorize;
- only the Planner commits:

```text
CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT
```

`PLAN_INTERRUPT` is the only directive that may carry a plan patch. Validate the patch against a copy of the graph before one durable commit.

Use `PBVCoordinator` for the physical handoff:

```text
BuilderOutput → Verifier → VerifierReport → Planner → PlannerDecision
```

## Massive collaboration and fleet admission

Before materially increasing worker count, run collaboration analysis.

Consider:

- dependency critical path;
- topological waves and parallel width;
- physical capacity;
- capability-eligible max-flow capacity;
- min-cut bottlenecks;
- coordination overhead;
- resource cost;
- marginal speed improvement.

Prefer the smallest worker count inside the near-optimal makespan band. Available workers are not automatically useful workers.

Fleet admission is opt-in and uses durable machine quota enforcement. It limits concurrent active work; it does not provision machines, credentials, model sessions, or cloud resources.

## Information-change checkpoints and additive steering

Represent changed assumptions, evidence, verification, contradictions, risk, external dependencies, or user steering as `ChangeSignal`.

When seed nodes are known, pause the seed set plus downstream dependency closure. Preserve unrelated active leases.

Only the authoritative Planner may resolve PBV change checkpoints. Resolve incrementally; unresolved nodes remain paused. Structural graph changes still require `PLAN_INTERRUPT`.

Do not invent evidence-to-plan dependencies. Record provenance and provide explicit plan-node anchors.

## Physical provisioning and worker lifecycle

Provisioning remains an external-effect layer after scheduling and admission:

```text
collaboration recommendation
→ optional admission quota
→ provisioning plan
→ proposed effect
→ explicit authorization
→ provider adapter
→ provider result
→ actual worker registration and heartbeat
```

A successful provider operation does not prove a healthy AASM worker exists.

Worker lifecycle controls are separate from provider teardown:

- `DRAIN`: reject new claims; allow current lease to finish.
- `RESUME`: restore worker admission.
- `OFFLINE`: reject work and release active leases.

Taking a worker OFFLINE does not delete its VM, pod, process, or container.

Replica-count providers cannot normally prove which logical AASM worker terminated. Mark a worker `DRAINING` only when the adapter explicitly confirms `drained_worker_ids`.

## Mission controls

Mission status is independent of machine state, Planner directives, change checkpoints, and worker state.

- `QUIESCE`: block all new task claims while active leases may finish.
- `SUSPEND`: commit the pause and release active leases.
- `RESUME`: reopen mission admission only.

Task claiming must check canonical mission state before and after ownership creation so stale workers cannot race past a pause.

Mission resume must not silently resume change-paused tasks, reactivate OFFLINE workers, authorize effects, or recreate released leases.

## Lease-loss semantics

A worker may finish local computation after suspension, expiry, worker OFFLINE, or another revocation released its lease.

Check the durable completion response. When ownership is gone, emit `LEASE_LOST`, not `COMPLETED`. Do not accept the result as successful task completion.

Cancelling/releasing a lease cannot undo an external side effect; those actions still require the effect/idempotency boundary.

## Controlled forks

Use the controlled path for network/operator workflows:

```text
ForkRequest
→ machine.fork effect proposal
→ explicit effect approval
→ execute_fork
```

The source event sequence and target machine ID belong to the idempotency boundary. Reject a target machine ID that already has different lineage.

Low-level `engine.fork()` remains for embedded callers that already own authority.

## Telemetry, artifacts, and cursors

Keep bounded telemetry in AASM and large logs/binaries in external backends referenced by stable IDs/URIs.

- New telemetry rows use stable `record_id`.
- New artifact rows use stable `artifact_id`.
- Page with opaque cursors.
- An expired retained anchor must produce an explicit cursor error.
- A cursor is not an authorization token.
- Artifact previews must be authenticated, size-bounded, and scoped to refs registered to the selected machine.

Observed task/task-class durations may feed later collaboration/fleet calculations unless the task explicitly locks its estimate.

## Runtime provider configuration

`aasm serve --runtime-config ...` may register Kubernetes, local-process, and Docker Compose provisioners plus memory/local-directory artifact backends.

- Execute explicit argv only; never shell-evaluate untrusted strings.
- Keep provider credentials/IAM outside the AASM config contract.
- Constrain local worker directories beneath an operator-configured root.
- Persist local process idempotency/PID state atomically.

## Required handoff payload

When handing work to another agent/worker, include:

- machine ID and version/event sequence;
- current machine and mission state;
- assigned task/frontier node;
- relevant graph neighborhood;
- constraints and invariants;
- evidence and assumption references;
- authorization scope;
- lease/checkpoint IDs where applicable;
- allowed response/control types;
- model/executor contract;
- artifact destination/reference rules.

## Safety and correctness

AASM improves process control. It does not make an underlying model correct. Security-sensitive, externally mutating, irreversible, or high-stakes domain actions require their own policies, credentials, validation, and human authority where appropriate.
