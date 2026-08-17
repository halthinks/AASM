# AASM v0.56.0 — Truthful Solver Outcomes

**Latest immutable published release:** v0.56.0  
**Current development target on `main`:** 0.56.1 — Execution Profiles + Runtime Provenance + Governed External Reality + Physical Authority + S3 Artifact/Entity Lineage  
**Released adoption contract:** `aasm.adoption.v1 / 0.32.0`  
**Active development adoption contract on `main`:** `aasm.adoption.v1 / 0.32.15`  
**Current qualified development boundary:** complete PR-3 / PHY-01 + S3 through artifact revision lineage and entity evolution  
**Next unfinished boundary:** S4 — Engineering + Safety Semantics (quantity/unit/tolerance foundation first)

AASM v0.56.0 is the latest published GitHub package/runtime release. Unreleased `main` now exposes the broader 0.56.1 development target and active adoption contract `0.32.15`, but that does **not** make v0.56.1 a published release. Exact unreleased source identity is the Git commit SHA.

The stable remote wire protocol remains **`aasm.remote.v1 / 0.19.0`** and is independent of package SemVer.

```text
latest published package: 0.56.0
published public surface: public_v56 / 0.32.0 at the v0.56.0 tag
current development target: 0.56.1 / 0.32.15 on main
qualified implementation head before documentation-only updates:
  6b107268cd4190357bf45b3bfd1385410a0d82cf
parent published release: v0.55.0
```

## Released v0.56.0 contracts

Truthful solver outcomes:

- `aasm.solver.outcome.v2`
- `aasm.solver.status.v2`
- `aasm.solver.termination.v2`
- `aasm.solver.evidence-grade.v1`
- `aasm.solver.status-v1-projection.v1`
- `aasm.solver.provider-status-map.v1`
- runtime `aasm.solver.outcome-v2.runtime.v1`

v0.56.0 preserves the complete v0.55 semantic-evolution, formulation, engineering-IR, and portable-archive foundation.

## What v0.56.0 changed

Solver outcome semantics no longer overload one status value with termination, feasibility, incumbent, proof, and provider-specific meaning.

A v0.56 outcome separates:

```text
termination cause
solution / feasibility state
incumbent presence
incumbent validation
optimality claim
bounds / relative gap
proof status
evidence grade
raw provider status + code
provider mapping identity
explicit legacy projection
```

A provider-returned assignment is not accepted as an incumbent merely because the provider returned values. AASM independently validates the assignment against the exact durable source model/request before it can support an incumbent-bearing outcome.

Provider status mapping is exact and versioned. Fuzzy or substring inference is forbidden; unknown future provider states remain unknown rather than being promoted from text fragments.

## Proof boundary

A provider `OPTIMAL` status plus an independently validated incumbent is still a provider optimality claim. It is not an independently checked proof of global optimality. The stronger proof/certificate boundary remains separate.

Likewise, a negative provider status does not silently become proof-grade infeasibility.

## Durability and authority

Solver Outcome v2 records use the existing AASM Evidence/event/reducer path. There is no parallel solver-result truth table.

```text
solver outcome normalization truth authority = NONE
provider claim != independent proof
```

## Current development after v0.56.0

`main` currently develops the coherent **0.56.1** candidate. It is no longer provenance-only.

### Execution profile + runtime provenance

Active contracts include:

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`

### PR-1 — governed state authority

Active contracts include:

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- runtime `aasm.state.authority.runtime.v1`

AASM keeps `DESIRED`, `PREDICTED`, `OBSERVED`, and `AUTHORITATIVE` state semantically distinct. Observation existence or agreement does not mint authority.

### PR-2 — governed external reality

Active contracts include:

- `aasm.machine.binding.v1`
- `aasm.machine.state-observation.v1`
- `aasm.machine.external.runtime.v1`
- `aasm.machine.transition.v1`
- `aasm.machine.transition.runtime.v1`
- `aasm.machine.postcondition-verification.v1`
- `aasm.machine.postcondition-verification.runtime.v1`

PR-2 supervises external authoritative state without creating a second external-truth table. Machine-transition proposals lower into the existing v0.54 Effect path. `EffectStatus.SUCCEEDED` does not by itself prove achieved physical/external state.

### PR-3A/3B — authority domains and leases

Active contracts include:

- `aasm.authority.domain.v1`
- `aasm.authority.lease.v1`
- runtime `aasm.physical.authority.runtime.v1`

Authority domains name bounded physical/effect authority namespaces. Authority leases establish exclusive time-bounded holders, strict monotonic epochs, revision binding, and append-only revocation. Domain or lease existence does not automatically grant `effect.authorize`.

### PR-3C/3D — bounded effect capabilities

Active contracts include:

- `aasm.effect.capability.v1`
- runtime `aasm.effect.capability.runtime.v1`

Capabilities are derived from active authority leases and must preserve or narrow operation sets, numeric bounds, validity, scope/revision identity, authority epoch, and delegation depth. Delegation cannot amplify authority.

### PR-3E/3F — stale-command fencing

Active capability-use semantics require exact current capability identity, lease identity, holder, authority epoch, revocation generation, scope/revision identity, operation, and numeric bounds.

Previously valid capability-use Evidence is not a reusable authorization token.

### PR-3G — semantic preemption + crash recovery

Active contracts include:

- `aasm.authority.preemption.v1`
- runtime `aasm.physical.control-fencing.runtime.v1`

Semantic preemption requires both authority-domain preemptor identity and existing scoped `physical.authority.preempt` permission. It uses canonical `AuthorityLease` revocation, invalidates stale capability authority, advances the required next epoch monotonically, and never rewrites Effect history or grants new Effect authority by existence.

Crash recovery repairs the narrow failure window where preemption Evidence became durable before canonical lease-revocation Evidence.

### PR-3H — implemented and gated

PR-3H integrates lease/capability/epoch/revocation/bounds checks into the **existing** `authorize_effect` / `execute_effect` path and rechecks live authority at both boundaries. It creates no second authority evaluator, scheduler, Effect dispatcher, ownership model, reconciliation path, or Effect truth store. The existing v0.54 Effect lifecycle remains authoritative.

### S3 — reality evidence, artifact lineage, and entity evolution

S3 is now gated through the observation/identity/calibration/trust/environment/fusion layers plus `aasm.artifact.revision.v1` / `aasm.artifact-lineage.runtime.v1` and `aasm.entity.evolution.v1` / `aasm.entity-evolution.runtime.v1`. Artifact revision identity is backend-independent and replayed through existing Evidence; storage binding is separate. Artifact existence or successful generation never implies authoritative acceptance. Entity evolution binds exact predecessor/successor artifact revision fingerprints and records split/merge/replacement/ambiguity without rewriting history. `AMBIGUOUS` mappings fail closed for hard automatic reuse. Neither subsystem creates a hidden current artifact/entity truth table or effect/fact authority.

## Exact-head qualification

The implementation head:

```text
6b107268cd4190357bf45b3bfd1385410a0d82cf
```

qualified the active `0.56.1 / 0.32.15` candidate with all 27 current custom commit-status contexts green, including:

- `aasm/ci-summary`
- `aasm/formal-assurance`
- `aasm/semantic-solver-rc`
- `aasm/proof-claims`
- `aasm/solution-pools`
- `aasm/optimization`
- `aasm/scoped-authority`
- `aasm/solver-learning`
- `aasm/v54`
- `aasm/v55`
- `aasm/v56`
- `aasm/v56-provenance`
- `aasm/state-authority`
- `aasm/external-machine`
- `aasm/machine-transition`
- `aasm/machine-postcondition`
- `aasm/physical-authority`
- `aasm/effect-capability`
- `aasm/physical-control-fencing`
- `aasm/physical-preemption-recovery`
- `aasm/physical-effect-integration`
- `aasm/identity-calibration-trust`
- `aasm/execution-environment`
- `aasm/observation-epistemics`
- `aasm/artifact-lineage`
- `aasm/entity-evolution`
- `aasm/physical-evidence`

The main CI matrix passed Python 3.11, 3.12, and 3.13, reproducible development-wheel smoke, PostgreSQL integration, Compose full-stack smoke, hierarchical scopes, LangGraph integration, and adapter conformance.

These are development/candidate capabilities until the selected release scope passes the deliberate release process and an explicit release operation publishes an immutable tag and artifacts.

See [`RELEASE_0.56.1.md`](RELEASE_0.56.1.md) for the candidate scope and [`VERSIONING.md`](VERSIONING.md) for the development/release identity policy.

## Release discipline

AASM no longer treats architecture milestones as automatic package releases.

A published package requires:

```text
deliberate release intent
        +
exact main SHA
        +
all required qualification gates
        +
strict tracked-file inventory
        +
reproducible build
        +
immutable tag/assets
        +
remote asset verification
```

Normal development is identified by Git SHA and named capability milestones. Package SemVer advances only at a deliberate release boundary.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
