# AASM v0.49.0 — Semantic Solver Release Candidate

AASM v0.49 is the release-candidate freeze of the semantic solver/control architecture assembled through v0.48. It adds assurance and compatibility surfaces over `runtime_v48.AASMEngine`; it does **not** add another scheduler, reducer, memory store, truth plane, authority mechanism, or inner solver kernel.

Runtime composition:

```text
SemanticSolverRCRuntimeMixin + runtime_v48.AASMEngine
```

## Contracts

```text
package/public surface: 0.49.0
aasm.adoption.v1 / 0.25.0
aasm.semantic.solver.rc.v1 / 0.1.0
stability: RELEASE_CANDIDATE
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.knowledge.cross-run.admission.v1 / 0.1.0
aasm.principal.cross-run-map.v1 / 0.1.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
license: Apache-2.0 project-wide declaration
```

## Release-candidate freeze

`semantic-solver-rc-freeze` emits a deterministic manifest over public contract IDs/versions, engine methods, CLI commands, imports, inspection surfaces, schemas, provider identities, replay expectations, and the project-wide Apache-2.0 licensing identity. The manifest fingerprint is the 0.49.x review target for intentional compatibility changes.

## Upgrade/replay compatibility

The RC runs durable upgrade fixtures:

```text
v0.41 → v0.49  event history + memo + governed memory
v0.47 → v0.49  governed SII policy + principal binding
v0.48 → v0.49  admitted cross-run knowledge + no authority inheritance
```

Every resumed fixture must reproduce the canonical snapshot hash and preserve the representative state introduced by that generation.

## Cross-backend certification

OR-Tools CP-SAT and HiGHS independently solve the same exact Boolean/integer optimization problem:

```text
x, y ∈ {0,1}
x + y >= 1
minimize x + y
```

Both must validate optimum `1`. CaDiCaL solves the corresponding Boolean feasibility projection `x OR y`.

```text
cross_backend_rule = AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE
```

Backend disagreement cannot become majority truth.

## Benchmark evidence

The RC measures semantic fingerprinting, event append/replay, direct CP-SAT execution, and the corresponding full provider → request → TaskLease → native solve → validation → Evidence lifecycle.

Timings are environment-specific measurements, not authority and not automatic performance claims:

```text
benchmark_policy    = MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM
native_solver_claim = AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS
```

## Claim-to-gate audit

The RC introduces:

```text
NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE
```

Claims about Python support, formal assurance, native solvers, cross-run governance, project-wide Apache licensing, and RC readiness are linked to concrete repository workflows/source gates.

## Required release gates

The dedicated **Semantic Solver RC** workflow installs the real optimization/modeling portfolio and executes the RC compatibility, real-backend, benchmark, public-CLI, and claim-audit suite. It publishes:

```text
aasm/semantic-solver-rc
```

The release workflow now requires the exact current `main` SHA to have:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
```

all at `success` before a package can be published.

## Existing authority boundaries preserved

```text
SEARCH_STATE_NEVER_PROMOTES_TRUTH
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION
REQUIRED VERIFICATION IS NEVER REDUCED BY SII
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY
```

Solver outputs remain Evidence. Search state remains performance state. Benchmark timing remains measurement. Cross-run knowledge remains foreign Evidence until receiving admission. SII remains resource economics rather than truth authority.

## Solver/formal portfolio

The complete released portfolio remains active:

- Kissat fast SAT;
- CaDiCaL direct/incremental SAT, assumptions and UNSAT cores;
- OR-Tools CP-SAT and scheduling;
- HiGHS MILP with warm starts/bounds/gap telemetry;
- CVXPY convex/QP/SOC;
- PuLP translation-only import;
- Z3 / cvc5 / Vampire / Lean 4 formal verification.

## Project-wide Apache-2.0 policy

AASM remains licensed under Apache-2.0 across the project through `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`. To the extent AASM has the necessary relicensing rights, prior AASM versions first distributed under MIT are also offered under Apache-2.0. Previously granted MIT permissions remain valid for their recipients; prior AASM versions are not designated MIT-only.

## Release identity

```text
package/public surface: 0.49.0
runtime: runtime_v49.AASMEngine
semantic base: runtime_v48.AASMEngine
solver/reuse kernel lineage: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.25.0
RC: aasm.semantic.solver.rc.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

See `docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md`, `docs/RELEASE_0.49.md`, `docs/CROSS_RUN_CERTIFIED_KNOWLEDGE.md`, and `LICENSE_POLICY.md`.
