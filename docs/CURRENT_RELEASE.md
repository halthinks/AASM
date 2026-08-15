# AASM v0.52.0 — Resource-Governed Multi-Objective Decisions & Pareto Solving

AASM v0.52.0 advances the public package/runtime to `0.52.0` and `aasm.adoption.v1 / 0.28.0`.

```text
runtime: runtime_v52.AASMEngine
parent runtime: runtime_v51.AASMEngine

aasm.optimization.multi-objective.v1 / 0.1.0
aasm.optimization.frontier.v1 / 0.1.0
aasm.resource.capacity.v1 / 0.1.0
aasm.resource.observation.v1 / 0.1.0
aasm.resource.demand.v1 / 0.1.0
aasm.resource.routing.v1 / 0.1.0
aasm.resource.runtime.v1 / 0.1.0
aasm.sii.resource-aware-proposal.v1 / 0.1.0
```

v0.52 unifies exact multi-objective decision semantics with governed real-world resource allocation while preserving the existing AASM commitment boundary.

## Exact finite multi-objective semantics

The lexicographic and exact Pareto solvers build on the v0.51 independently certified complete finite enumeration substrate rather than creating a second optimizer kernel.

Lexicographic stages preserve higher-priority optima outside only explicitly declared tolerance. Exact finite Pareto `COMPLETE` requires an independently reconstructed nondominated set over the certified complete feasible space.

The Pareto certificate checks full point identity:

```text
solution ID + assignment + objective vector
```

Reusing a valid solution ID with forged point contents fails certification. Pareto dominance is tolerance-aware: no-worse comparisons honor tolerance and strict improvement must exceed it.

All optimization results and completeness certificates remain `EVIDENCE_ONLY`; they never grant policy or truth authority.

## Resource-governed decisions

A resource-aware SII successor proposal explicitly binds:

```text
correctness
evidence quality
expected progress
resource demand / upper bound
provider quota burn
scarce expert usage
monetary cost
wall time
```

Provider quota burn is its own proposal dimension, not inferred from provider names or another resource field.

`ResourceRoutingPolicy` carries an explicit ordered objective vector. Hard quality/capacity gates run before preference ordering.

Resource capacity supports fixed, rolling, refilling, credit-balance, unbounded, and unknown windows. Provider observations retain `AUTHORITATIVE | OBSERVED | DERIVED | ESTIMATED | DECLARED | UNKNOWN` provenance. Accepted observations may conservatively reduce planning capacity but can never create capacity beyond the declared envelope.

Protected reserve, atomic multi-resource reservation, re-estimation (`CONTINUE | REPLAN_REQUIRED`), release, settlement, and predicted-versus-actual calibration are durable through the existing Evidence/event history.

## Two different Pareto completeness scopes

1. **Exact finite optimization frontier:** exact and independently certified over the complete supported finite feasible model space.
2. **Resource-candidate frontier:** exact over the supplied eligible candidate set only; it does not claim undiscovered routes do not exist.

Resource-candidate Pareto analysis is non-committing Evidence. It reserves no capacity. Selection/reservation is a separate commitment step.

## Authority boundary

```text
RESOURCE STATE NEVER GRANTS AUTHORITY.
RESOURCE OBSERVATIONS REMAIN EVIDENCE.
OPTIMALITY / PARETO COMPLETENESS REMAIN EVIDENCE.
SII UTILITY NEVER BUYS TRUTH OR STATE AUTHORITY.
```

## Exact-SHA release gates

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
```

`aasm/optimization` is published only after the dedicated v0.52 contract/adversarial suite and the real native optimization/modeling suite both pass.

Next: **v0.53 — Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening**.

AASM remains an `0.x` active-development project with no presumed v1.0. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
