# AASM v0.55.0 — Governed Semantic Evolution and Engineering IR

AASM v0.55.0 makes governed semantic evolution and engineering-grade mathematical representation part of the active public runtime.

## Active surface

- package/runtime: `0.55.0`
- public surface: `public_v55`
- runtime: `runtime_v55.AASMEngine`
- adoption contract: `aasm.adoption.v1 / 0.31.0`
- parent release: v0.54.0

## What v0.55 adds

### Durable semantic evolution

`ExternalReference`, `ProblemRevision`, and `ProblemDelta` provide stable external identity, revision lineage, deterministic change description, and stale-revision fencing. Revision history is reconstructed from the existing Evidence/event stream; v0.55 does not create a second truth store or change-impact graph.

### Governed solver formulations

`SolverFormulation` binds source and target models, provider capability manifests, model-admission reports, exact object mappings, external engineering references, and optional problem-revision identity. Formulations must be durably registered before an execution request can be bound, and revision-bound formulations fail closed after their source revision is superseded.

The built-in formulation checker certifies exact identity formulations only. Non-trivial translations require an independent checker for the requested fidelity.

### Exact pseudo-Boolean and cardinality IR

AASM now has typed pseudo-Boolean and cardinality constraints with deterministic exact linearization, source-to-target mapping, external-reference lineage, and an independent lowering checker. Approximate lowering is not claimed by this contract.

### Portable scheduling semantics

The scheduling IR represents integer tasks, precedence with lag, no-overlap, cumulative resources, exact assignment validation, problem-revision binding, and provider capability admission. Non-integral resource demands fail closed.

This release does **not** claim that the generic CP-SAT worker is a complete scheduling execution adapter. The scheduling contract is a portable semantic/model and validation foundation.

### Deterministic quadratic and conic representation

Continuous engineering models use canonical decimal strings for deterministic representation, `Decimal`-based independent assignment validation, named numeric tolerance policies, quadratic expressions/constraints/objectives, and standard second-order-cone constraints.

Structural exactness and numerical feasibility are kept distinct. Assignment validation does **not** claim convexity, global optimality, or an optimality proof.

### Governed decision vectors

Hard floors are constraints, never optimization objectives. Candidates that violate a hard floor are excluded before lexicographic comparison. Remaining linear objectives can compile into the existing exact finite multi-objective engine only when the semantics are genuinely representable. No weighted scalarization is introduced.

### Portable semantic archive

`SemanticEvolutionArchive` exports canonical snapshot material, complete durable event history, and derived v0.55 projections with section fingerprints plus a root fingerprint. Verification replays the archived events through the existing AASM reducer and compares the resulting canonical state to the persisted snapshot.

Durable event sequence numbers are ordering provenance; they are not equated with machine state version. Derived projections are not replay inputs and grant no truth authority.

## Claim ceilings

v0.55 intentionally preserves these boundaries:

- semantic-evolution truth authority: existing AASM admission path only;
- solver-formulation truth authority: none;
- pseudo-Boolean/cardinality approximation: not supported by the exact IR contract;
- scheduling execution adapter: not claimed by this foundation;
- continuous assignment validation: no optimality proof;
- decision-vector scalarization: none;
- semantic-archive replay: archived event sequence only; persisted snapshot is comparison evidence, not replay input.

## Release qualification

The dedicated `aasm/v55` workflow is read-only and verifies:

- tracked-file inventory;
- exact pseudo-Boolean/cardinality contracts;
- scheduling contracts;
- deterministic quadratic/conic contracts;
- governed decision-vector contracts;
- semantic-archive contracts;
- revision/runtime/formulation/model-admission fixtures;
- the active `public_v55` root surface.

The ordinary project release gates remain authoritative for repository-wide publication and distribution checks.

## Next

v0.56 may build truthful solver outcome normalization, execution provenance, and reproducibility certification on this released v0.55 boundary. Those capabilities are not part of v0.55.
