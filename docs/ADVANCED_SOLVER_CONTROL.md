# Advanced Solver Control & Search Artifacts

AASM v0.46 extends the v0.44/v0.45 heterogeneous solver portfolio with explicit search controls and solver-native artifacts while preserving one authority plane.

Contract: `aasm.optimization.advanced.v1 / 0.1.0`.

The governing rule is **SEARCH_STATE_NEVER_PROMOTES_TRUTH**. Every advanced solver output remains `EVIDENCE_ONLY`; resource utility, solver bounds, UNSAT cores, incumbents, and learned search state cannot directly authorize AASM knowledge or mutate canonical state.

## Execution boundary

All five advanced provider classes use the existing path:

```text
Advanced problem
  -> CapabilityContract
  -> POLICY / CONTROLLER provider admission
  -> ResourceRecord
  -> WorkerRecord
  -> TaskDemand
  -> TaskLease
  -> native solver
  -> independent AASM validation
  -> Evidence
  -> optional v0.41 reuse admission
```

Expired leases, superseded attempts, provider/implementation mismatches, result-ID collisions, and non-idempotent completed-lease submissions are rejected.

## Fast SAT — Kissat

`solver.sat.fast@0.1.0` uses Kissat through PySAT's dedicated `Kissat404` binding. It is the non-incremental high-performance SAT route. Kissat's PySAT binding does not expose aggregate statistics; AASM records that limitation as telemetry rather than converting a successful solve into an error.

## Incremental SAT — CaDiCaL

`solver.sat.incremental@0.1.0` uses incremental CaDiCaL through PySAT and supports:

- assumptions;
- UNSAT core extraction over assumptions;
- conflict budget;
- decision budget;
- bounded in-process solver-session reuse.

Learned solver state is **EPHEMERAL_PERFORMANCE_ONLY**. It is not a durable AASM claim, is not a reusable truth object, and can be deleted without changing canonical meaning. Durable UNSAT-core Evidence is bound to the exact request, assumptions, provider, and model fingerprint.

## CP-SAT scheduling

`solver.cp_sat.scheduling@0.1.0` extends the existing OR-Tools CP-SAT path with first-class scheduling structures:

- fixed and optional interval variables;
- `NO_OVERLAP` constraints;
- `CUMULATIVE` resource constraints;
- explicit search-worker count;
- deterministic-time budget;
- conflict, branch, deterministic-time, and wall-time telemetry.

AASM independently rechecks interval equations, active-interval overlap, cumulative load, base constraints, and objective values before admitting successful result Evidence.

## Advanced MILP — HiGHS

`solver.milp.advanced@0.1.0` extends the existing HiGHS path with:

- warm start submission;
- MIP relative-gap target;
- node limit;
- primal/dual bound telemetry;
- MIP gap telemetry;
- node and simplex-iteration telemetry.

A warm start is a performance hint only. It cannot change the canonical model or weaken feasibility checking.

## Advanced convex optimization — CVXPY

`solver.convex.advanced@0.1.0` adds a richer AASM-owned convex representation without making arbitrary CVXPY expressions canonical.

The v0.46 advanced convex IR supports:

- scalar continuous variables;
- linear constraints;
- factorized positive-semidefinite quadratic minimization;
- factorized negative-semidefinite quadratic maximization;
- cross terms through weighted squares of linear forms;
- affine second-order-cone constraints of the form `||A x + b||₂ <= cᵀx + d`.

The factor representation makes convexity structural: non-negative factor weights form a PSD quadratic for minimization, while AASM negates the factor contribution for concave maximization. The runtime independently re-evaluates constraints and the canonical objective before Evidence admission.

## Reuse

Advanced solver results reuse the existing v0.41 `OPTIMIZATION_RESULT` plane. A prior result does not skip execution merely because it exists. POLICY/CONTROLLER must admit a `ReuseCandidate`, normal scope/environment/dependency/effect validation must pass, and a `ReuseCertificate` must be committed before the solver loop can return `SKIP_EXECUTION`.

Ephemeral incremental-SAT learned state is intentionally outside this durable reuse plane.

## Verification

The `Optimization Backends` workflow installs the real optional optimization stack on Python 3.13 and requires:

- legacy CaDiCaL SAT lifecycle tests;
- legacy OR-Tools CP-SAT lifecycle tests;
- legacy HiGHS lifecycle tests;
- v0.45 CVXPY/PuLP real tests;
- v0.46 Kissat real execution;
- v0.46 incremental CaDiCaL assumptions, UNSAT core, and session reuse;
- v0.46 CP-SAT scheduling execution;
- v0.46 HiGHS warm start and bound/gap telemetry;
- v0.46 advanced CVXPY execution;
- `advanced-optimization-conformance --real`.

Formal Assurance continues to model-check the shared optimization lease/Evidence authority boundary. v0.46 adds source-contract gates ensuring the new search artifacts remain non-authoritative rather than inventing a second formal kernel.

## Known deliberate limits

v0.46 does not yet make learned SAT clauses durable governed objects, does not expose arbitrary dense `Q` matrices as the canonical convex input, does not exchange MILP cut pools or LP bases across runs, and does not translate bounds/conflicts between solver families without a certificate. Those remain explicit future solver work rather than hidden backend metadata.
