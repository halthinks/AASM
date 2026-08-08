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
2. Instantiate `AASMEngine(ProblemSpec(...))`. When the workflow has a domain-specific control graph, load a `MachineDefinition` and run `check_machine()` before execution. For long-running or recoverable work, provide a durable store such as `SQLiteStore`.
3. Move only through legal machine transitions. Never mutate `snapshot.state` directly.
4. Run `engine.classify()` in `CLASSIFY` to select applicable algorithmic operators.
5. Represent nontrivial dependencies as a `PlanGraph`; prefer topological execution for DAGs and shortest path when alternatives have costs.
6. Create a checkpoint before branching, irreversible work, or a high-risk assumption.
7. Use `DPMemory` for equivalent solved subproblems; attach validity scope and invalidate when assumptions change.
8. Use `ResourceFlowAllocator` when work competes for bounded agents, tools, concurrency, or budget; inspect minimum-cut edges before adding workers.
9. Before COMMIT or irreversible action, call adversarial verification and resolve blocking counterexamples.
10. Agents may propose actions. The configured `AuthorityPolicy` decides who can authorize them. The runtime, not generated prose, owns authoritative state.
11. Emit evidence and provenance for every material transition. Do not bypass the event-sourced transition/patch APIs by mutating durable snapshot fields directly.
12. For durable runs, recover with `AASMEngine.resume(machine_id, store)` or `recover_unfinished(store)` and verify replay before resuming risky external work.
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
When an action has an external side effect, represent it as an `EffectSpec`, persist it before execution, authorize it explicitly, and execute it through `execute_effect()`. Reuse stable idempotency keys for semantically identical operations. Never blindly retry an `UNKNOWN` effect outcome; reconcile external state first unless the executor is explicitly retry-safe.

## Durable planning and evidence
Use `engine.plan_add_node`, `plan_add_edge`, `plan_update_node`, `plan_mark_visited`, and `plan_prune_node` instead of mutating `engine.graph` when plan state must survive restart or replay. Use `memo_put`/`memo_get`/`memo_invalidate` for persistent subproblem reuse. Record claims, observations, assumptions, and contradictions through the evidence APIs, and link derived records with stable evidence IDs.

## Durable resource scheduling
When work competes for constrained agents, tools, model slots, GPUs, API quotas, or human review capacity, register them with `ResourceRecord` and express work as `TaskDemand`. Use `engine.schedule()` rather than manually assigning workers when capability/capacity constraints matter. Treat `result.bottlenecks` and `result.unmet` as planner evidence: adding workers outside the min-cut does not improve throughput. Resource/schedule state is replayable and fork-aware.

## Distributed worker rule
When work may be executed by multiple processes or machines, register workers against durable resources and use `claim_task()` rather than assigning ownership only in conversational state. Heartbeat long-running leases, reap stale workers, and use quotas for bounded concurrency/capacity. SQLite task claims are atomic per `(machine_id, task_id)` so concurrent workers cannot both reserve the same unexpired task. After another process advances a machine, resume from the durable store before continuing from that process.
