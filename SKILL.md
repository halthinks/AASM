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
- `planner_builder.yaml`: executable Planner/Builder/Verifier profile; Planner/Builder is not the core architecture.
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

## Governance economics
Use `GovernanceContext` and `engine.governance_decide()` when deciding whether a *semantic model review* is needed. This decision does not authorize execution. Sandbox policy, authority policy, credentials, effect authorization, network policy, and destructive-operation guards remain separate and must still pass.

A governance fingerprint should identify the material action and the revisions that make a prior review valid: action class, scope, action signature, policy revision, assumption revision, and evidence revision. Prefer a stable diff/artifact/action digest for `action_signature` over a generic label.

A completed low-risk review may be reused only when that fingerprint is unchanged. Never automatically reuse review for destructive, credential, security-sensitive, external-write, unknown-network, irreversible, or unknown actions. `assumption_changed` and `tests_failed` force a fresh review regardless of fingerprint reuse.

Configure soft/hard governance budgets with `GovernanceBudgetPolicy`. Ratio thresholds are sample-aware and should not fire before `min_total_tokens_for_ratio_enforcement`. Soft pressure may route review to a lower-cost eligible reviewer. Hard pressure returns `BUDGET_PAUSE`; it must never convert required review into permission.

After a required review completes, call `complete_governance_review(decision_id, evidence=...)`. Record the actual reviewer model call separately as `CallPurpose.PERMISSION_REVIEW` so governance overhead and cache-adjusted cost remain measurable.

Use `governance_report()` to inspect budget state, deterministic bypasses, reused reviews, and conservative avoided-overhead estimates. Avoided token/cost estimates use the run's observed average permission-review call when available; treat them as counterfactual estimates, not billing facts.

## Executable Planner / Builder / Verifier profile
Use `initialize_team()` with exactly one enabled `PLANNER` plus any number of Builders and Verifiers. The registered Planner is the sole owner of authoritative plan mutation.

Builders submit `BuilderOutput`. They may report artifacts, diffs, tests, assumptions, and evidence, but they do not issue control directives or modify the plan.

Verifiers submit `VerifierReport`. They may recommend one of `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT`, and AASM records a deterministic policy recommendation from verification signals, but neither recommendation is authority.

Only the Planner may commit `PlannerDecision`. `PLAN_INTERRUPT` is the only directive that may include a `plan_patch`; it must include one. Apply the patch against a copied plan graph and validate it before committing. A failed/cyclic patch must leave the existing plan revision unchanged.

Use `PBVCoordinator` to automate the physical handoff:

`BuilderOutput → Verifier callable → VerifierReport → Planner callable → PlannerDecision`.

Planner and Verifier callables can be real model executors, remote services, deterministic code, or humans. Preserve the source `verifier_report_id` when the Planner overrides a recommendation. A changed assumption or unexpected output should lead to explicit Planner reasoning and, when the plan must change, an explicit `PLAN_INTERRUPT`; never silently infer and rewrite the plan.

## Massive collaboration and worker fan-out
Before increasing worker count materially, run `engine.analyze_collaboration()` or the `aasm collaboration` command. Do not equate available workers with useful parallelism.

The collaboration analysis must consider the dependency critical path, topological execution waves, maximum parallel width, physical resource capacity, capability-eligible max-flow capacity, min-cut bottlenecks, resource cost, and coordination overhead. Treat the recommendation as Planner evidence.

A worker that cannot satisfy a task capability does not count as useful capacity. A serial critical path caps useful concurrency even when hundreds of workers are available. Adding workers outside the current min-cut or above the DAG parallel width does not improve throughput.

Prefer the smallest worker count within the configured near-optimal makespan band. Use `min_relative_improvement` to reject extra workers whose marginal speedup is negligible and `coordination_overhead_per_extra_worker` to represent real communication/integration cost.

The collaboration planner does **not** authorize or provision infrastructure. Provisioning workers, cloud resources, external services, or additional model sessions remains a separate deployment/authority decision. Re-run collaboration analysis after a `PLAN_INTERRUPT`, material task-duration change, capability change, or resource-fleet change because those can alter the critical path or useful ceiling.

## Information-change checkpoints and additive steering
When user steering, changed assumptions or evidence, failed verification, contradictions, risk escalation, or external dependencies invalidate work, represent the change as a `ChangeSignal`. Anchor `seed_nodes` whenever the affected plan location is known. The affected region is the seed set plus its downstream dependency closure; do not globally pause the run when only one subgraph is invalidated.

Call `engine.analyze_change()`. With selective pause enabled, AASM durably adds the affected nodes to the pause set and releases only affected active leases. Unaffected active leases remain valid. `claim_task()` checks the canonical pause state before and after ownership is created, so a stale worker process must not bypass a newly committed checkpoint.

An unanchored `ChangeSignal` still requires Planner attention, but it must not falsely mark every plan node affected. Assumption and evidence IDs are provenance unless the caller supplies the plan-node anchors that they invalidate.

When the executable PBV profile is configured, only the authoritative Planner may call `resolve_change_impact()`. Resolve incrementally: `resume_nodes` and `retire_nodes` must be subsets of the checkpoint's current `remaining_nodes`. A `PARTIAL` checkpoint stays resolvable, and nodes already resumed in an earlier resolution must not be re-paused by a later one.

If the authoritative plan itself must change, the Planner must commit an explicit `PLAN_INTERRUPT`. Link that Planner decision through `plan_decision_id` when resolving the affected checkpoint. `retire_nodes` only clears task validity in the checkpoint; structural plan removal/pruning still belongs in the Planner's explicit plan mutation.

A `user_interrupt()` with `metadata.seed_nodes` is additive steering: preserve the existing plan and provenance, pause only the impacted dependent region, and continue unaffected work. Do not regenerate the whole plan simply because a new requirement arrived.

Change-impact analysis controls task validity, not permission or security. Sandbox rules, governance review, authority policy, credentials, external-effect authorization, and destructive-operation guards remain separate boundaries.

## Automatic checkpoint triggers and fleet admission
Use `CheckpointTriggerPolicy` to decide which explicit Verifier findings automatically become selective change checkpoints. Failed tests, changed assumptions, unexpected output, and blocking findings may trigger by default. Automatic checkpointing pauses invalidated work; it does **not** grant the Verifier plan authority.

When `PBVCoordinator` submits a Verifier report, the Planner payload includes the resulting trigger, affected/remaining nodes, paused tasks, and current fleet-control state. The Planner may resolve part of an impact through `PlannerDecision.metadata.resolve_impact`, but only explicitly listed nodes may resume or retire. A structural plan change still requires `PLAN_INTERRUPT` with a validated `plan_patch`.

Fleet admission is opt-in through `FleetControlPolicy`. When enabled, call `configure_fleet_control()` or `refresh_fleet_control()` to re-run collaboration analysis on currently runnable scheduled tasks. Paused, completed, and pruned work must be excluded before computing useful concurrency.

The resulting admission limit is enforced through AASM's existing machine-scoped `QuotaPolicy`, not a process-local counter. This is important: SQLite/PostgreSQL then enforce fleet admission atomically at the same task-claim boundary as other durable quotas.

Fleet control limits active admitted work; it does not provision machines, model sessions, cloud instances, credentials, or external services. Collaboration analysis remains evidence and fleet enforcement remains separately configurable. Deployment authority is not implied by a worker recommendation.

Recalculate fleet admission after an automatic checkpoint, Planner `PLAN_INTERRUPT`, or change-impact resolution when the policy enables those refreshes. Avoid duplicate recalculation when one Planner decision both resolves a checkpoint and changes the plan.

Inspect this loop through `checkpoint-triggers`, `checkpoint-trigger-policy`, `fleet-control`, and `fleet-refresh`, or the equivalent remote endpoints. The Control Center should make recommendation vs enforcement visibly distinct.

## Physical fleet provisioning and live telemetry
Treat physical provisioning as a separate external-effect layer after collaboration analysis and fleet admission. `plan_fleet_provisioning()` may compute a desired worker delta, but that plan is evidence only and must not create, destroy, or drain infrastructure by itself.

Convert a chosen `ProvisioningRequest` into a durable effect with `propose_provisioning()`. An authority must explicitly call `authorize_effect()` before `execute_provisioning()` may invoke a `ProvisioningAdapter`. Provider credentials, cloud IAM, network policy, billing controls, and provider-specific safeguards remain outside and in addition to AASM authorization.

Use a stable provider adapter through `ProvisioningRegistry` for server-side execution. If the control plane has no registry or no matching provider, provisioning execution must fail closed. Do not infer provider behavior from a string name.

A successful PROVISION effect does not prove that an AASM worker exists or is healthy. The actual worker process must connect, register, and heartbeat before it is usable. A successful DRAIN effect may move only explicitly targeted registered workers into `DRAINING`; do not silently drain busy workers merely to satisfy a numerical target.

Remote workers automatically emit `STARTED`, `COMPLETED`, and `FAILED` execution telemetry. Custom workers/executors may also stream `LOG`, `PROGRESS`, `ARTIFACT`, and `HEARTBEAT` records. Keep large log bodies and artifacts outside the bounded telemetry ledger and record stable references instead.

Use completed telemetry duration as scheduling evidence. When `TelemetryPolicy.use_observed_durations` is enabled, observed task/task-class mean duration may replace future `estimated_duration` before collaboration/fleet analysis. Set `metadata.lock_estimated_duration=true` when a task's declared estimate must remain authoritative.

Record completion telemetry only after the lease is durably completed. This ensures telemetry-driven fleet refresh sees canonical finished state and does not re-count the just-completed task as runnable.

Keep recommendation, enforcement, and physical provisioning visibly distinct:

`collaboration recommendation → optional fleet admission quota → explicit provisioning plan → authorized provider effect → worker registration/heartbeat`.

Telemetry is evidence, not authority. Observed timing may change scheduling/fleet recommendations, but it must never authorize deployment, plan mutation, credentials, external effects, or destructive actions.
