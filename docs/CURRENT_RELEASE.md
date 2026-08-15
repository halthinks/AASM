# AASM v0.53.0 — Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening

AASM v0.53.0 advances the public package/runtime to `0.53.0` and `aasm.adoption.v1 / 0.29.0`.

```text
active public surface: public_v53
active runtime: runtime_v53_learning.AASMEngine
parent public surface: public_v52
parent runtime: runtime_v52.AASMEngine

aasm.identity.scoped.v1 / 0.1.0
aasm.authority.scoped.v1 / 0.1.0
aasm.authority.scoped.runtime.v1 / 0.1.0
aasm.store.scoped.v1 / 0.1.0
aasm.solver.learning.v1 / 0.1.0
aasm.solver.learning.runtime.v1 / 0.1.0
aasm.solver.learning.application.v1 / 0.1.0
```

v0.53 hardens AASM's public control plane around identity, authority, persistence access, distributed resource ownership, external effects, and reusable solver learning without creating a second truth or scheduler plane.

## Scoped identity and authority

AASM now distinguishes `Principal`, `Workspace`, `Machine`, and `Scope` as separate durable concepts. Authority is explicit, scoped, replayable, and fail-closed:

```text
no grant => DENY
matching DENY => overrides ALLOW
authority expiry => denied
cross-run authority transfer => NEVER
resource state => never grants authority
```

Delegation cannot exceed the issuer's active delegable capability, scope, or remaining delegation depth. Delegated wildcard authority is forbidden.

## Scope-safe persistence access

`aasm.store.scoped.v1` is the public v0.53 persistence seam for raw reads. Cross-workspace access, ambiguous multi-workspace raw snapshots, child-scope raw machine access, and legacy unscoped effect reads fail closed. The facade exposes no direct append or mutation API; writes remain governed runtime transitions.

## Resource ownership and distributed commit safety

v0.53 resource mutations require explicit scoped capabilities for capacity registration, observations, reservation, re-estimation, release, and settlement. Resource history derives actor provenance from the exact durable authority Evidence that authorized the mutation.

Resource-state Evidence commits carry an optimistic machine-version precondition. Two hosts planning from the same resource version cannot both commit conflicting reservations: the stale writer fails and reloads canonical state. This behavior is verified on MemoryStore, SQLite, and PostgreSQL.

## External effects

Effect proposal is scope-bound, but proposal does not authorize execution. Authorization, execution, and reconciliation are distinct scoped capabilities. Every external execution attempt receives a fresh authority decision, so expired or revoked authority cannot be bypassed by retry behavior. UNKNOWN reconciliation remains separately governed.

## Durable cross-run solver learning

v0.53 introduces durable learned solver artifacts:

```text
correctness-sensitive:
  NO_GOOD
  UNSAT_CORE
  BOUND

performance-only:
  INCUMBENT
  WARM_START
  NATIVE_ACCELERATOR
```

Cross-run transfer reuses the existing v0.48 `CrossRunKnowledgeEnvelope(kind="REUSE_RESULT")` and receiving-run admission path. Admission preserves provenance but does not make foreign learning true or authoritative.

Correctness-sensitive artifacts remain inert until the receiving run revalidates them against the exact model. For supported finite models, pruning/bound claims are checked against the independently certified complete feasible solution set.

## Explicit solver-learning application

`aasm.solver.learning.application.v1` separates validation from application. Application requires the exact PASS validation, the exact artifact/model binding, and scoped `solver.learning.apply` authority.

```text
truth_authority  = NONE
policy_authority = NONE
```

Certified pruning is lowered into a new `OptimizationModel` and executed through the existing optimization provider path. Validated incumbent/warm-start hints remain performance-only; the existing OR-Tools CP-SAT adapter consumes supported assignments using `CpModel.add_hint(...)` and reports the consumed application IDs.

## Exact-SHA release gates

v0.53 publication requires success on the exact current `main` commit from:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
aasm/scoped-authority
aasm/solver-learning
```

The release workflow then builds two byte-identical distributions, clean-installs the wheel, validates the active public contract, publishes the GitHub release once, and verifies every remote release asset byte.

Next: **v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery**.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
