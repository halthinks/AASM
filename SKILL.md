---
name: aasm-algorithmic-agent-state-machine
description: Use AASM to structure an AI task as a durable algorithmic state machine with explicit legal transitions, durable graph planning, persistent memoization, evidence lineage, external-effect control, and configurable authority.
---

# AASM Skill

## When to use
Use AASM for multi-step, branchy, stateful, expensive, auditable, multi-agent/tool, or failure-recoverable work. Do not assume Planner/Builder; AASM is role-agnostic.

## Operating rules
1. Formalize goal, objective, constraints, invariants, acceptance tests, and structural features.
2. Instantiate `AASMEngine(ProblemSpec(...))`; use `SQLiteStore` for recoverable work.
3. Load a `MachineDefinition` and run `check_machine()` when the workflow has a custom control graph.
4. Move only through legal transitions; never mutate authoritative state directly.
5. Use durable plan APIs (`plan_add_node`, `plan_add_edge`, `plan_update_node`, `plan_mark_visited`, `plan_prune_node`) for plan state that must survive restart/replay.
6. Use `memo_put` / `memo_get` / `memo_invalidate` for persistent dynamic-programming memory with validity scopes and proof references.
7. Record claims, observations, assumptions, and contradictions through the evidence APIs. Link derived records with stable evidence IDs and invalidate rather than delete stale evidence.
8. Create checkpoints before branching, irreversible work, or high-risk assumptions.
9. Represent external side effects as durable `EffectSpec` records, authorize them explicitly, reuse stable idempotency keys, and reconcile `UNKNOWN` outcomes before retrying.
10. Use `ResourceFlowAllocator` for bounded agents/tools/concurrency/budget and inspect min-cut bottlenecks before adding workers.
11. Run adversarial verification before COMMIT or irreversible action.
12. Recover with `AASMEngine.resume()` / `recover_unfinished()`; inspect history with `replay(at_sequence=N)` and create alternate futures with `fork(N)`.
13. Treat a fork as a new machine. Historical planning, memory, and evidence copy only up to the fork boundary; prior external effects do not copy.
14. COMPLETE only when acceptance tests are satisfied.

## Failure semantics
- local defect → `REPAIR`
- invalid ancestor decision → `BACKTRACK`
- insufficient/contradictory evidence → `INVESTIGATE`
- better costed route → relax the graph and preserve provenance
- resource bottleneck → reallocate using flow/min-cut
- external dependency/user block → `PAUSE`

## Required handoff payload
Machine id/version, state, problem spec, assigned frontier node, graph neighborhood, constraints/invariants, relevant memo keys, evidence IDs/lineage, authorization scope, checkpoint if applicable, and allowed response types.

## Safety
AASM improves process control; it does not make model outputs correct. High-stakes and irreversible actions require domain-specific validation and authority policy.
