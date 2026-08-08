---
name: aasm-algorithmic-agent-state-machine
description: Use AASM to structure an AI task as a durable algorithmic state machine with explicit legal transitions, graph planning, backtracking, memoization, resource allocation, evidence checks, and configurable authority.
---

# AASM Skill

## When to use
Use this skill for tasks that are multi-step, branchy, stateful, expensive to repeat, require auditable plan changes, involve multiple agents/tools, or need deterministic failure recovery.

Do not assume Planner/Builder. AASM is role-agnostic. Select an orchestration profile or define agents by capability.

## Operating rules
1. Formalize the goal into objective, constraints, invariants, acceptance tests, and structural features.
2. Instantiate `AASMEngine(ProblemSpec(...))`. When the workflow has a domain-specific control graph, load a `MachineDefinition` and run `check_machine()` before execution. For long-running or recoverable work, provide a durable store such as `SQLiteStore` or `PostgresStore`.
3. Move only through legal machine transitions. Never mutate `snapshot.state` directly.
4. Run `engine.classify()` in `CLASSIFY` to select applicable algorithmic operators.
5. Represent nontrivial dependencies as a `PlanGraph`; prefer topological execution for DAGs and shortest path when alternatives have costs.
6. Create a checkpoint before branching, irreversible work, or a high-risk assumption.
7. Use `DPMemory` for equivalent solved subproblems; attach validity scope and invalidate when assumptions change.
8. Use `ResourceFlowAllocator` when work competes for bounded agents, tools, concurrency, or budget; inspect minimum-cut edges before adding workers.
9. Before COMMIT or irreversible action, call adversarial verification and resolve blocking counterexamples.
10. Agents may propose actions. The configured `AuthorityPolicy` decides who can authorize them. The runtime, not generated prose, owns authoritative state.
11. Emit evidence and provenance for every material transition. Do not bypass the event-sourced transition/patch APIs by mutating durable snapshot fields directly.
12. `AASMEngine.resume(machine_id, store)` and `recover_unfinished(store)` are passive by default. When a process actually crashed with unresolved external effects, opt in explicitly with `recover_effects=True` before reconciling those effects.
13. Use `engine.replay(at_sequence=N)` to inspect historical state without re-running effects. Use `engine.fork(N)` for alternate futures; treat the fork as a new machine and explicitly propose any new external effects.
14. COMPLETE only when acceptance tests are satisfied; FAIL is terminal and must state why.

## Profiles
- `single_agent.yaml`: one agent, reversible autonomous actions.
- `planner_builder.yaml`: compatibility profile; Planner/Builder is not the core architecture.
- `expert_swarm.yaml`: specialist agents with quorum governance.
- `hierarchical_team.yaml`: delegated local authority with central/human gates.
- `quorum_governance.yaml`: multi-party authorization.
- `human_in_loop.yaml`: human authorization for configured external/irreversible actions.

## Required handoff payload
When another agent receives AASM work, give it: machine id/version, current state, problem spec, assigned task/frontier node, relevant graph neighborhood, constraints/invariants, evidence references, authorization scope, checkpoint id if applicable, and allowed response types.

## Failure semantics
- Local defect with preserved assumptions → `REPAIR`
- Ancestor decision invalid → `BACKTRACK`
- Evidence insufficient / contradiction unresolved → `INVESTIGATE`
- Better costed path discovered → relax the plan graph, preserve provenance
- Resource bottleneck → run max-flow/min-cut, reallocate rather than blindly spawn agents
- User or external dependency blocks progress → `PAUSE`

## Safety and correctness
AASM improves process control; it does not make an underlying model correct. External side effects, security-sensitive actions, or domain-specific high-stakes decisions require their own policies and validation.

## Durable effect rule
When an action has an external side effect, represent it as an `EffectSpec`, persist it before execution, authorize it explicitly, and execute it through `execute_effect()`. Reuse stable idempotency keys for semantically identical operations. Never blindly retry an `UNKNOWN` effect outcome; reconcile external state first unless the executor is explicitly retry-safe. Passive resume/inspection must not reclassify a healthy remote worker's `RUNNING` effect; crash reconciliation is an explicit recovery operation. SQLite and PostgreSQL atomically claim effect attempts so only one executor crosses the external side-effect boundary for a given attempt.

## Durable planning and evidence
Use `engine.plan_add_node`, `plan_add_edge`, `plan_update_node`, `plan_mark_visited`, and `plan_prune_node` instead of mutating `engine.graph` when plan state must survive restart or replay. Use `memo_put`/`memo_get`/`memo_invalidate` for persistent subproblem reuse. Record claims, observations, assumptions, and contradictions through the evidence APIs, and link derived records with stable evidence IDs.

## Durable resource scheduling
When work competes for constrained agents, tools, model slots, GPUs, API quotas, or human review capacity, register them with `ResourceRecord` and express work as `TaskDemand`. Use `engine.schedule()` rather than manually assigning workers when capability/capacity constraints matter. Treat `result.bottlenecks` and `result.unmet` as planner evidence: adding workers outside the min-cut does not improve throughput. Resource/schedule state is replayable and fork-aware.

## Distributed worker rule
When work may be executed by multiple processes or machines, register workers against durable resources and use `claim_task()` rather than assigning ownership only in conversational state. Heartbeat long-running leases, reap stale workers, and use quotas for bounded concurrency/capacity. SQLite task claims are atomic for local multi-process coordination; PostgreSQL applies the current canonical worker/resource/quota policy under database locks for real multi-host execution. After another process advances a machine, resume from the durable store before continuing from that process.

## Remote execution and model routing
For multi-host operation, run the AASM control plane against `PostgresStore` and have remote workers use `AASMRemoteClient` for registration, heartbeat, claim, lease renewal, and completion. Stateless control-plane handlers should use lazy resume (`load_history=False`) so worker heartbeats and dashboard polling do not replay the full event history; full replay/export remains available when verification requires it. Preserve the lease/effect distinction: a lease grants task ownership, while externally visible side effects still require effect idempotency/reconciliation.

Treat model choice as resource routing when model classes differ materially in strength, latency, context, or cost. Register `ModelProfile` records and route with `ModelRouteRequest`; do not hard-code expensive models for tasks that meet their quality floor on a cheaper class, and do not route high-risk architecture/review work below its minimum strength contract. The selected model is a control-plane decision; the executor adapter must translate it into the actual provider/Codex/API invocation.

## Executor orchestration
For work that should actually run on remote machines, put an `execution` object in `TaskDemand.metadata`. At minimum provide `prompt`; add model/executor capability floors, `min_strength`, context/cost constraints, or fixed model/executor IDs only when the task contract requires them.

Run physical workers with `OrchestratedRemoteWorker` or `aasm worker`. Register worker-local executors with `ExecutorRegistry`/`ExecutorBinding`; never treat the existence of a model route as proof that an executable provider adapter exists. The worker must complete this chain explicitly:

`lease → execution contract → model route → executor selection → provider/Codex invocation → usage/evidence capture → durable completion/failure`.

Report returned `ModelUsageRecord` through the control plane before lease completion. Worker restarts may reuse a durable `worker_id` only when the resource binding is unchanged.

## Adaptive model routing
Use adaptive routing only from **explicit evaluated outcomes**. Execution success, a non-error API response, or a completed lease is not by itself evidence that the model's work was accepted.

Classify repeatable work with a stable `task_class`. After verification, record `ModelOutcomeRecord` with the model used plus accepted/rejected status, repair requirement, verification score, latency, cost, executor, and relevant provenance. Use `record_model_outcome()` locally or `AASMRemoteClient.model_outcome()` remotely.

Static routing remains authoritative for eligibility. Empirical history may re-rank eligible models but must never weaken configured capability, minimum-strength, context, enabled-state, candidate-set, or cost-ceiling constraints. Apply empirical acceptance floors to the Wilson lower bound, not the raw observed rate. `ModelPerformance.confidence` means concentration of the Wilson acceptance interval (`1 - interval width`), not probability that the model is correct.

When evidence is insufficient, retain the deterministic static route. Enable `explore_under_sampled` only when deliberate calibration is wanted; calibration deterministically selects an eligible under-sampled model rather than randomizing production work.

Use `empirical_optimize=cost_per_quality` when the goal is the least-cost model with demonstrated conservative quality, `quality` for the strongest measured acceptance, or `latency` for measured speed among statically eligible models. Keep task classes narrow enough that their outcomes are meaningfully comparable.

## Model economics and review efficiency
Treat model calls as resource consumption with purpose. Record productive, verification, governance, permission-review, synthesis, and retry usage separately, including cached-input reads and explicit cache-write tokens when the provider exposes them. Prefer deterministic rules for routine benign permission decisions; escalate to model review when assumptions change, tests fail, the change is materially large, or the operation is destructive, credential-related, security-sensitive, externally mutating, or irreversible.

Do **not** weaken sandboxing, network policy, credential boundaries, or destructive-operation guards to save tokens. Use `ReviewGatePolicy` and Codex rules to remove redundant semantic review only where the permission decision is already expressible deterministically. Use model intelligence where changed information genuinely requires judgment.

When using `OpenAIResponsesExecutor` or `CodexCLIExecutor`, record returned usage with `engine.record_model_usage()` or the remote model-usage endpoint so the Control Center can expose cache-adjusted productive-vs-governance cost. If governance overhead grows disproportionately, change checkpoint cadence, deterministic rules, or model routing before simply adding more reviewer agents.
