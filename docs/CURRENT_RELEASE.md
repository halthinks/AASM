# AASM v0.55.0 — Governed Semantic Evolution and Engineering IR

AASM v0.55.0 is the active public package/runtime and advances the adoption contract to `aasm.adoption.v1 / 0.31.0`.

The stable remote wire-protocol compatibility surface remains **`aasm.remote.v1 / 0.19.0`**. That protocol version is intentionally independent of the package/runtime release version.

```text
active public surface: public_v55
active runtime: runtime_v55.AASMEngine
parent public surface: public_v54
parent runtime: runtime_v54_full.AASMEngine
remote wire protocol: aasm.remote.v1 / 0.19.0

semantic evolution:
  aasm.external.reference.v1
  aasm.problem.revision.v1
  aasm.problem.delta.v1
  aasm.semantic-evolution.runtime.v1

solver formulation:
  aasm.solver.formulation.v1
  aasm.solver.formulation-certificate.v1
  aasm.solver.formulation-execution-binding.v1
  aasm.solver.formulation-runtime.v1

engineering IR:
  exact pseudo-Boolean/cardinality
  portable scheduling semantics
  deterministic quadratic/conic representation
  governed decision vectors
  portable semantic-evolution archive
```

v0.55 extends v0.54 without adding a second truth store, scheduler, resource ledger, or effect lifecycle.

## Governed semantic evolution

External engineering identities, problem revisions, and deltas are explicit durable objects. Revision transitions are reconstructed from existing Evidence and events. A revision-bound operation fails closed while truth-maintenance work is pending or after its source revision is superseded.

## Solver formulation governance

A solver formulation binds the exact source/target models, provider capability manifest, model-admission report, object mappings, external-reference mappings, and optional problem revision. Execution requests may only be bound to a durably registered formulation with a passing governance chain.

The built-in formulation checker is deliberately limited to exact identity formulations. Non-trivial translations require an independent checker for the requested fidelity.

## Exact discrete IR

Pseudo-Boolean and cardinality constraints have deterministic exact linearization with independent checking and preserved external-reference lineage. Approximate lowering is not claimed.

## Scheduling IR

Portable scheduling models cover integer tasks, precedence, no-overlap, cumulative resources, exact assignment validation, revision binding, and provider capability admission. Resource capacities/demands must be positive integers.

`execution_adapter = NOT_CLAIMED_BY_THIS_FOUNDATION` remains an explicit release boundary.

## Continuous quadratic/conic IR

Continuous models use canonical decimal strings and named numeric tolerance policies. The independent validator supports linear/quadratic expressions and standard second-order-cone constraints using deterministic `Decimal` evaluation.

Exact structural representation is distinct from numerical satisfaction under tolerance. `optimality_proof = NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION`.

## Governed decision vectors

Hard floors are constraints, not weighted objectives. Only hard-floor-compliant candidates enter lexicographic comparison. Linear criteria may compile to the released exact-finite multi-objective engine when semantics match exactly. `scalarization = NONE`.

## Portable semantic archive

The archive contains canonical snapshot material, complete event history, and derived v0.55 projections with section fingerprints and a root fingerprint. Verification replays the archived event sequence through the existing AASM reducer and compares canonical state with the persisted snapshot.

Event sequence numbers provide durable ordering; they are not machine-version counters. Derived projections grant no truth authority and are never replay inputs.

## Exact release boundary

The dedicated `aasm/v55` gate is read-only and checks inventory, all v0.55 engineering contracts, semantic-evolution/formulation fixtures, replay/archive behavior, and the active `public_v55` surface.

Repository-wide release publication remains gated by the ordinary AASM CI/formal/solver/release workflows. See `docs/RELEASE_0.55.md` for the release-specific capability and claim summary.

Next: **v0.56.0 — Truthful Solver Outcomes, Runtime Provenance, and Reproducibility**.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
