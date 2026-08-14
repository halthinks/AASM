# AASM v0.50.0 — Proof-Carrying Solver Claims

v0.50 establishes a proof-carrying claim layer over the v0.49 Semantic Solver RC while preserving the existing AASM authority boundary.

```text
package/public surface: 0.50.0
aasm.adoption.v1 / 0.26.0
aasm.solver.proof-certificate.v1 / 0.1.0
stability: EXPERIMENTAL_ENFORCED
license: Apache-2.0 project-wide declaration
```

## What is new

- exact-bound `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` objects;
- `SOLVER_VALIDATED` versus `PROOF_CERTIFIED` verification levels;
- `PROOF_CERTIFIED` requires an independent checker and PASS;
- `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` exhaustively certifies bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
- deterministic trace digests and independent reconstruction/recheck;
- proof applicability is explicit: unsupported continuous domains, uncovered claim kinds, and over-budget exhaustive spaces remain `UNSUPPORTED` rather than being misreported as proof failures;
- false optimality/negative claims fail closed and never create a certificate;
- durable proof records reuse AASM's existing Evidence/event history and exact replay;
- JSON Schema 2020-12 claim/artifact/certificate contracts;
- bounded TLA+ and Promela/SPIN invariants for independence, binding, PASS, failure/unsupported exclusion, and policy-only truth authorization;
- public `solver-proof-contract` and `solver-proof-conformance` CLI;
- dedicated exact-head `aasm/proof-claims` release gate.

## Authority law

```text
PROOF_CERTIFIED = independently checked Evidence
PROOF_CERTIFIED != POLICY AUTHORITY
certificate_authority = EVIDENCE_ONLY
truth_authority = EXISTING_AASM_POLICY_ONLY
```

## Deliberate limits

v0.50 does not claim native proof-object support for every backend or mathematical family. DRAT/LRAT-style SAT proofs, MILP proof formats, dual certificates, unboundedness rays, and theorem-prover-native proof transport require future dedicated checker/gate work before receiving proof-grade labels.

## Release gates

The exact release commit must have all of:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
```

at `success`. Release artifacts remain reproducible, clean-install tested, historically audited, and remotely byte-verified before publication succeeds.
