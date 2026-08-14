# AASM Heterogeneous Solver Portfolio

## Status

Implemented in AASM v0.44.0.

Contract:

```text
aasm.optimization.v1 / 0.1.0
```

This release extends the existing v0.39 Capability ABI and v0.41 solver/reuse loop. It does not add a second scheduler, reducer, event log, or truth store.

## Goal

AASM should own the canonical problem representation, decomposition boundary, durable execution state, provider admission, scheduling, result normalization, evidence, reuse, and certification while mature native solvers own their optimized inner loops.

```text
                           AASM
                            |
                 Canonical Constraint IR
                            |
        +---------+---------+---------+--------------------+
        |         |         |         |                    |
       SAT      CP-SAT     MILP      SMT/FOL             PROOF
        |         |         |         |                    |
    CaDiCaL   OR-Tools    HiGHS   Z3 / cvc5 / Vampire    Lean 4
        |         |         |         |                    |
        +---------+---------+---------+--------------------+
                            |
                  normalized Evidence
                            |
                 v0.41 validated reuse
                            |
               reasoning / certification
```

## Existing formal pathway preserved

The v0.39 formal-verification pathway remains unchanged:

- Z3 — SMT-LIB2 through `formal.smt`;
- cvc5 — SMT-LIB2 through `formal.smt`;
- Vampire — TPTP through `formal.first_order`;
- Lean 4 — kernel checking through `formal.proof_kernel`.

Those providers remain VERIFIER capabilities and their results remain Evidence until the existing v0.37 epistemic admission policy accepts them.

The v0.44 optimization providers are different: they are OPERATOR capabilities that produce optimization-result Evidence. They do not gain epistemic authority.

## New provider pathway

### SAT — CaDiCaL

Provider ID: `cadical`

Capability:

```text
solver.sat@0.1.0
```

Execution uses PySAT's CaDiCaL binding. AASM lowers a pure Boolean/clause model into a deterministic integer-literal CNF mapping and invokes the native CaDiCaL solver through PySAT.

The SAT adapter supports exact Boolean assignment recovery and solver statistics. SAT/UNSAT remains provider Evidence; an UNSAT result is not silently turned into an AASM truth assertion.

### CP-SAT — OR-Tools

Provider ID: `ortools-cp-sat`

Capability:

```text
solver.cp_sat@0.1.0
```

AASM lowers Boolean/integer variables, clauses, linear integer constraints, all-different constraints, and integer linear objectives into OR-Tools CP-SAT.

For deterministic reference execution, the adapter uses one search worker and a fixed random seed. The request timeout is mapped to CP-SAT's time limit.

### MILP — HiGHS

Provider ID: `highs`

Capability:

```text
solver.milp@0.1.0
```

AASM lowers continuous/integer/Boolean variables, linear constraints, and a linear objective into the `highspy` modelling API.

The request timeout is mapped to HiGHS. Returned primal assignments are independently rechecked against the canonical AASM model before durable result admission.

## Canonical Constraint IR

AASM owns the canonical optimization identity.

### Variables

Domains:

```text
BOOL
INTEGER
CONTINUOUS
```

Every variable has a stable `variable_id` and explicit lower/upper bounds.

### Constraints

Supported v0.44 primitives:

```text
CLAUSE
LINEAR
ALL_DIFFERENT
```

`CLAUSE` is SAT-native and CP-SAT compatible.

`LINEAR` supports `<=`, `>=`, and `==`.

`ALL_DIFFERENT` is CP-SAT-native.

### Objective

A single linear objective may be:

```text
MINIMIZE
MAXIMIZE
```

### Family selection

The canonical model can declare `AUTO`, `SAT`, `CP_SAT`, or `MILP`.

`AUTO` is deterministic:

1. a pure Boolean clause model with no objective selects SAT;
2. an integer/Boolean model representable by CP-SAT selects CP-SAT;
3. a linear model representable by MILP selects MILP;
4. a model not representable by these v0.44 lowerings is rejected instead of guessed.

## Existing AASM execution path

The exact execution sequence is:

```text
OptimizationModel
      |
      v
ordinary AASM Evidence admission
      |
      v
OptimizationRequest
      |
      v
ordinary AASM Obligation
      |
      v
TaskDemand with capability + provider tokens
      |
      v
existing ResourceRecord / WorkerRecord scheduler
      |
      v
existing TaskLease
      |
      v
native solver adapter
      |
      v
OptimizationResult
      |
      v
AASM validates request/model/provider/lease/assignment
      |
      v
ordinary Evidence
```

No optimization backend can bypass the existing resource/worker lease boundary.

## Provider admission

The standard v0.39 Capability ABI remains authoritative.

A provider must be admitted by `POLICY` or `CONTROLLER` authority. Registration creates or validates:

- an existing `CapabilityContract`;
- a `ResourceRecord` with capability/provider tokens;
- a `WorkerRecord` bound to that resource;
- an admitted `CapabilityProvider`.

The optimization runtime does not create a separate provider registry.

## Result validation

A successful assignment (`SAT`, `FEASIBLE`, or `OPTIMAL`) is not trusted merely because a backend returned it.

Before durable admission AASM deterministically checks:

- exact request fingerprint;
- exact model fingerprint;
- exact leased task/provider;
- admitted provider/capability compatibility;
- variable bounds;
- integer/Boolean integrality;
- every supported clause;
- every supported linear constraint;
- every all-different constraint;
- objective value against the returned assignment.

Provider claims of UNSAT/INFEASIBLE are retained as solver Evidence. v0.44 does not pretend to independently prove those claims without a proof/certificate path.

## Result authority

Optimization results are explicitly:

```text
EVIDENCE_ONLY
```

A solver cannot directly:

- authorize reasoning;
- mutate canonical truth;
- create POLICY authority;
- skip the AASM lease boundary;
- admit its own result as reusable truth.

The bounded TLA+ and Promela models assert that a solver result requires a task lease, a committed solver result creates Evidence, and truth authorization requires a separate policy action.

## Reuse

Optimization reuses the existing v0.41 mechanism.

`optimization_reuse_request(request_id)` produces an ordinary `ReuseRequest` containing the exact optimization request/model fingerprints plus environment and dependency fingerprints.

A completed optimization result is **not automatically reusable**. A policy/controller must admit a `ReuseCandidate` referencing the durable optimization-result Evidence. A future exact request may then be discharged only after ordinary v0.41 validation and `ReuseCertificate` commit.

Therefore:

```text
native solver result
        !=
automatic execution skipping
```

The path remains:

```text
result Evidence
   -> policy reuse admission
   -> reuse lookup
   -> validation
   -> ReuseCertificate
   -> solver-loop SKIP_EXECUTION
```

## Real-backend verification

The repository contains a dedicated `Optimization Backends` GitHub Actions workflow.

It installs:

```text
python-sat
ortools
highspy
```

and executes:

1. real CaDiCaL SAT solve;
2. real OR-Tools CP-SAT optimization;
3. real HiGHS MILP optimization;
4. AASM provider registration;
5. AASM task scheduling;
6. AASM lease claiming;
7. native backend execution;
8. result validation and Evidence commit;
9. obligation completion;
10. exact replay.

The workflow also executes:

```bash
aasm optimization-conformance --real
```

and requires all three native-backend checks to report `PASS`.

## v0.44 implementation phases

### Phase 1 — Canonical IR

Delivered:

- variables, constraints, objective, model/request/result identities;
- deterministic family inference;
- JSON schemas;
- deterministic assignment/result validation.

### Phase 2 — Native workers

Delivered:

- PySAT/CaDiCaL adapter;
- OR-Tools CP-SAT adapter;
- HiGHS adapter;
- normalized statuses and runtime statistics.

### Phase 3 — AASM runtime integration

Delivered:

- v0.39 capability admission reuse;
- resource/worker registration;
- ordinary TaskDemand and TaskLease execution;
- durable model/request/result Evidence;
- obligation lifecycle integration.

### Phase 4 — Reuse

Delivered:

- exact optimization `ReuseRequest` generation;
- policy-gated reuse candidate admission via existing v0.41 APIs;
- certificate-gated solver-loop execution skipping.

### Phase 5 — Assurance

Delivered:

- dependency-neutral regression suite;
- real native-backend integration suite;
- release/source gates;
- TLA+ authority-boundary model;
- Promela/SPIN authority-boundary model.

## Deliberate v0.44 limits

The initial IR is intentionally smaller than the union of every native backend feature.

Not yet canonicalized:

- incremental SAT assumptions/unsat cores as first-class AASM objects;
- pseudo-Boolean/cardinality constraints beyond lowerable primitives;
- CP-SAT intervals/no-overlap/cumulative scheduling constraints;
- MILP SOS, indicator, quadratic, nonlinear, and advanced cut-control constructs;
- warm starts/bases/incumbents as reusable governed artifacts;
- solver portfolio racing or cross-solver bound sharing;
- proof logging for SAT/MILP infeasibility;
- cross-run solver-state persistence.

These should be added as explicit canonical contracts rather than hidden backend-specific metadata.

## Next solver work

The next solver-performance layer should focus on:

1. incremental SAT assumptions, cores, and learned-clause provenance;
2. CP-SAT scheduling primitives and deterministic-time budgets;
3. MILP incumbent/bound/cut telemetry and warm starts;
4. portfolio policies that choose/race SAT, CP-SAT, MILP, SMT, FOL, and proof-kernel routes;
5. translation certificates when one canonical model is lowered into different solver representations;
6. certified cross-solver conflict/bound reuse.

SII remains above this plane. Its resource economics can later allocate real SAT conflict budgets, CP-SAT deterministic time, MILP node/iteration budgets, formal-verification budget, and reasoning/context budget without receiving epistemic authority.
