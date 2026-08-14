# AASM v0.50.0 — Proof-Carrying Solver Claims

AASM v0.50 adds proof-grade solver-claim certification over the v0.49 Semantic Solver RC runtime without adding another scheduler, reducer, memory store, solver kernel, or authority plane.

Runtime composition:

```text
ProofClaimRuntimeMixin + runtime_v49.AASMEngine
```

## Contracts

```text
package/public surface: 0.50.0
aasm.adoption.v1 / 0.26.0
aasm.solver.proof-certificate.v1 / 0.1.0
proof stability: EXPERIMENTAL_ENFORCED
aasm.semantic.solver.rc.v1 / 0.1.0
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
license: Apache-2.0 project-wide declaration
```

## Proof boundary

```text
SOLVER STATUS != PROOF GRADE
SOLVER_VALIDATED != PROOF_CERTIFIED
```

`PROOF_CERTIFIED` requires exact problem/formulation/model/result binding, an independent checker, and PASS. The initial checker `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` exhaustively certifies supported bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims.

Continuous variables, unsupported claim families, and proof spaces beyond the configured finite-domain budget are `UNSUPPORTED`, not proof failures. Contradicted claims are `FAIL`. Neither can produce `PROOF_CERTIFIED`.

## Durability and authority

Claims, proof artifacts, and certificates are recorded through the existing Evidence/event history and must replay exactly.

```text
certificate_authority = EVIDENCE_ONLY
truth_authority       = EXISTING_AASM_POLICY_ONLY
```

A proof certificate strengthens Evidence; it does not directly authorize truth or canonical state.

## Required release gates

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
```

All must be `success` on the exact current `main` SHA before release publication.

## Release identity

```text
package/public surface: 0.50.0
runtime: runtime_v50.AASMEngine
parent runtime: runtime_v49.AASMEngine
adoption: aasm.adoption.v1 / 0.26.0
proof claims: aasm.solver.proof-certificate.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

See `docs/PROOF_CARRYING_SOLVER_CLAIMS.md`, `docs/RELEASE_0.50.md`, `docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md`, and `LICENSE_POLICY.md`.
