# Semantic Dependency Graph and Truth Maintenance

AASM v0.38 turns admitted knowledge into an explicit causal/dependency structure without creating another source of truth.

## One authoritative machine

The dependency graph is a deterministic projection over state that already belongs to the AASM machine:

- semantic problem entities, predicates, objectives, operators, observers, and verifiers;
- v0.37 reasoning artifacts, verification records, and Evidence;
- decision-calculus constraints, decisions, and obligations;
- durable events and effects;
- explicit dependency edges admitted as ordinary Evidence.

There is no dependency-specific database, reducer, event log, scheduler, or private mutable graph.

## Edge direction

Every propagating edge points from an upstream premise/cause toward the object whose validity depends on it.

```text
premise → claim → decision → obligation
```

Therefore:

- forward traversal answers **what breaks if X changes?**;
- reverse traversal answers **what is the lineage behind Y?**.

## Cycle policy

Edges with `propagates_stale=true` must form a DAG. A propagating cycle makes the graph invalid and cannot be admitted through `register_semantic_dependency`.

Descriptive relationships may cycle only when `propagates_stale=false`. This lets the graph preserve useful non-causal associations without making invalidation ambiguous.

## Truth-maintenance protocol

Truth change is a two-record durable protocol.

### 1. Record plan

A verifier, policy authority, or controller identifies the root node and reason. AASM computes its affected descendants and stores a `TruthMaintenancePlan` as Evidence **before applying changes**.

The plan contains:

- root node;
- affected node closure;
- reason;
- authority identity/class;
- graph fingerprint at planning time;
- evidence IDs;
- deterministic plan ID/fingerprint.

### 2. Apply idempotently

The recorded closure is applied through existing AASM mechanisms:

- nonterminal reasoning artifacts become `STALE` through the v0.37 reasoning transition path;
- terminal `REFUTED`/`REJECTED` artifacts remain terminal;
- dependent active/proposed causal decisions become `INVALIDATED` and are removed from active models;
- obligations that already consumed the invalidated truth move to `NEEDS_REVALIDATION` only where that transition is already legal;
- untouched `AVAILABLE` obligations remain available;
- locks are reevaluated through the existing calculus lock machinery.

A completion Evidence record identifies the applied plan and result fingerprint.

If a process stops after planning but before completion, `resume_truth_maintenance(plan_id)` finishes the same plan. If completion already exists, reapplication is a no-op.

## Locality invariant

Truth maintenance affects the root plus its registered affected descendants. It does not invalidate unrelated siblings merely because they share a machine or scope.

This locality is essential for long-horizon work: changing one premise should reopen only work that depends on that premise.

## Causal decisions

`CausalDecisionRecord` extends the existing `DecisionRecord` with:

- rejected alternatives;
- confidence;
- reasoning text;
- causal event IDs;
- causal reasoning-artifact IDs.

The record remains inside the existing calculus. V0.38 does not introduce a parallel decision system.

## Reactive obligations

A `ReactiveObligationRule` is policy-admitted and watches durable event types. A matching event deterministically derives an ordinary `ObligationRecord` containing its trigger provenance and declared `handler_name`.

**Derivation never calls the handler.**

That separation is deliberate:

```text
Event → rule match → durable Obligation
```

V0.39 will type the handler and capability ABI. V0.41 will execute obligations through the autonomous solver loop.

## Preparing Hierarchical Memory

V0.40 — Hierarchical Memory, Reasoning Frontier, and Context Projection — must not create an independent truth system. V0.38 therefore exposes deterministic projection signals that memory/context selection can consume:

- `VALID`;
- `STALE`;
- `REFUTED`;
- `AUTHORIZED`;
- scope visibility;
- dependency depth;
- causal relevance;
- objective relevance;
- last verification time;
- verification strength;
- supersession lineage.

Canonical memory can later retain durable content/reference identity while vector, lexical, graph, and learned retrieval representations remain derived indexes.

## Formal assurance

The v0.38 bounded TLC/SPIN model checks:

- completion requires a previously recorded plan;
- only affected descendants become stale;
- unrelated siblings remain untouched;
- dependent decisions invalidate;
- consumed work reopens for revalidation;
- reactive derivation never executes a handler.
