# Generic Calculus Observability

AASM v0.25 exposes the machine's durable reasoning state through domain-neutral projections rather than domain-specific dashboards.

## Core views

`AASMEngine.inspect_machine(surface)` supports:

- `summary` — combined machine observability report;
- `decisions` — Decision Graph;
- `obligations` — Obligation Graph;
- `evidence` — Evidence Graph;
- `conflicts` — conflict, explanation, learned-constraint, and backjump timeline;
- `fairness` — persistent-obligation fairness debt;
- `packages` — profile binding and migration history;
- `candidates` — decision-backend and candidate lifecycle state;
- `assurance` — certificate, verification, history-check, and minimization counts;
- `calculus` — raw formal-calculus projection;
- `profile` — bound profile package state.

## Graph semantics

The Decision Graph presents planning decisions, status, levels, pinned assignments, and dependency edges.

The Obligation Graph presents conditional obligations and their dependency edges. Decision-to-obligation edges use the generic `AUTHORIZED_BY` relation.

The Evidence Graph projects durable evidence records and explicit `SUPPORTS`, `CONTRADICTS`, and `DERIVED_FROM` relations when present.

## Timelines

Observability includes conflict history plus event-derived records for backjumps, search restarts, profile changes, candidate decisions, and assurance activity.

## Fairness debt

Fairness records expose hidden epochs, continuous lock epochs, lock counts, and review/enabled history. This makes starvation risk visible without embedding any particular domain meaning into the kernel.

## Design boundary

A profile package may supply presentation hints outside the kernel, but the built-in observability model remains based on generic AASM objects. A research package, engineering package, business process, human workflow, or autonomous software system can therefore use the same inspection surfaces.
