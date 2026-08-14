# AASM v0.50 — Proof-Carrying Solver Claims

v0.50 adds proof-grade claim certification without changing AASM's authority boundary, scheduler, reducer, solver kernels, memory plane, or truth-admission path.

## Core law

```text
SOLVER STATUS != PROOF GRADE
```

A native solver result remains Evidence. A negative or optimality claim may additionally become `PROOF_CERTIFIED` only when an independent checker validates a proof artifact bound to the exact problem, formulation, model, and result.

```text
solver result
    ↓
SolverClaim                 SOLVER_VALIDATED
    ↓
SolverProofArtifact         untrusted until checked
    ↓
independent checker
    ↓
SolverClaimCertificate      PROOF_CERTIFIED only on PASS
```

The contract is:

```text
aasm.solver.proof-certificate.v1 / 0.1.0
stability = EXPERIMENTAL_ENFORCED
certificate_authority = EVIDENCE_ONLY
truth_authority = EXISTING_AASM_POLICY_ONLY
```

## v0.50 proof checker

The first AASM-owned checker is:

```text
aasm.checker.finite-domain-exhaustive.v1 / 0.1.0
```

It independently exhausts bounded Boolean/integer domains and can certify:

- `UNSAT` — no Boolean assignment satisfies the exact SAT model;
- `INFEASIBLE` — no bounded discrete assignment satisfies the exact canonical model;
- `OPTIMAL` — every bounded discrete assignment is examined and the claimed objective equals the global optimum.

The checker records domain sizes, states examined, feasible count, exact problem/formulation/model/result fingerprints, and a deterministic trace digest. Verification re-runs the exhaustive checker and requires the artifact to reproduce exactly.

## Unsupported is not failure

Continuous variables, claims outside the v0.50 checker scope, or a finite search space larger than the configured proof budget are `UNSUPPORTED`.

```text
UNSUPPORTED != FAIL
```

`FAIL` means an applicable checker contradicted the claim—for example, a supposedly infeasible model has a feasible assignment, or a supposedly optimal assignment has a better feasible alternative.

Neither `UNSUPPORTED` nor `FAIL` can produce `PROOF_CERTIFIED`.

## Durability

Claims, artifacts, and certificates are persisted through the existing AASM Evidence/event history. v0.50 does not add a proof database or alternate reducer. Exact replay must reproduce the same durable proof projection.

## Authority

Proof certification strengthens evidence; it does not authorize truth or state by itself.

```text
PROOF_CERTIFIED = independently checked Evidence
PROOF_CERTIFIED != POLICY AUTHORITY
```

All existing AASM laws remain intact:

```text
SEARCH_STATE_NEVER_PROMOTES_TRUTH
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION
REQUIRED_VERIFICATION IS NEVER REDUCED BY SII
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY
```

## Deliberate v0.50 limits

v0.50 does not claim proof-producing support for every native backend or mathematical family. Native DRAT/LRAT-style SAT proofs, MILP infeasibility/optimality proof formats, dual certificates, unboundedness rays, and theorem-prover-native proof transport remain future checker/plugin work unless a dedicated reproducible gate is added.

The release criterion is narrower and enforceable: **no AASM claim is labeled `PROOF_CERTIFIED` unless a registered independent checker verifies exact claim bindings and the checker reports PASS.**
