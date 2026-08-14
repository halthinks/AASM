# AASM v0.49 — Semantic Solver Release Candidate

v0.49 is a contract-freeze and assurance release over the v0.48 runtime. It is intentionally **not** a new scheduler, reducer, memory system, truth plane, solver kernel, or authority mechanism.

The runtime shape is:

```text
SemanticSolverRCRuntimeMixin + runtime_v48.AASMEngine
```

## RC contract

```text
aasm.semantic.solver.rc.v1 / 0.1.0
stability: RELEASE_CANDIDATE
freeze target: 0.49.x
compatibility floor exercised by RC migration fixtures: v0.41
cross_backend_rule: AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE
native_solver_claim: AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS
claim_policy: NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE
```

The RC exists to convert remaining architecture claims into reproducible evidence and freeze the coherent public surface before a later stable semantic-solver line.

## 1. Public contract freeze

`build_semantic_solver_rc_freeze_manifest()` captures and fingerprints:

- all discoverable public contract IDs and versions;
- supported engine methods;
- CLI commands;
- public imports;
- inspection surfaces;
- JSON schemas;
- solver/provider identities;
- persistence/replay expectation;
- Apache-2.0 + `LICENSE_POLICY.md` licensing identity.

The freeze manifest does not prevent future changes by magic. It gives CI and release tooling a stable, machine-readable object against which intentional compatibility changes can be reviewed.

## 2. Upgrade and replay compatibility

The RC migration fixture creates durable histories using released runtime generations and resumes them under the RC engine:

```text
v0.41 → v0.49
  event history
  memoized value
  governed v0.40 memory

v0.47 → v0.49
  governed SII scoring policy
  durable SII principal binding

v0.48 → v0.49
  admitted cross-run knowledge
  foreign-authority non-inheritance
```

Each resumed history must replay to the exact canonical snapshot hash and preserve the representative state introduced by that generation.

This is a compatibility fixture, not a claim that arbitrary undocumented private implementation details from every historical commit are frozen forever.

## 3. Cross-backend certification

The RC includes an exact overlapping discrete optimization problem:

```text
x, y ∈ {0,1}
x + y >= 1
minimize x + y
```

The problem is represented independently as:

- CP-SAT and solved by OR-Tools;
- MILP and solved by HiGHS.

Both must independently validate and return optimum `1`.

A Boolean feasibility projection is also solved by CaDiCaL:

```text
x OR y
```

That result must satisfy the projected feasibility property.

The RC never turns backend agreement into voting authority. The frozen rule is:

```text
cross_backend_rule = AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE
agreement          → corroborating Evidence
conflict           → INCONCLUSIVE / investigate
majority           → NEVER grants truth
```

CVXPY, Kissat, advanced CaDiCaL, advanced HiGHS, and scheduling remain covered by their existing real conformance gates rather than being forced into a semantically different overlap problem.

## 4. Benchmark evidence

`run_rc_benchmarks()` measures:

- canonical semantic fingerprint workload;
- event append/replay workload;
- when native dependencies are present, direct CP-SAT solve time;
- the corresponding full AASM provider-admission/request/TaskLease/execute/validate/Evidence lifecycle;
- observed orchestration-overhead ratio.

Timing values are environment-specific evidence. The RC deliberately does **not** convert them into an unsupported performance claim.

```text
inner_solver_claim  = NONE
native_solver_claim = AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS
```

AASM does not claim its orchestration layer makes CaDiCaL, OR-Tools, HiGHS, CVXPY, Z3, cvc5, Vampire, or Lean internally faster. Performance claims require an explicit threshold gate and benchmark methodology.

## 5. Claim-to-gate audit

The RC audits important public claims against repository evidence. Examples:

- Python 3.11/3.12/3.13 support → CI matrix;
- bounded formal assurance → Formal Assurance workflow;
- native solver portfolio → Optimization Backends workflow;
- cross-run governance → Cross-Run Knowledge workflow;
- project-wide Apache-2.0 policy → `LICENSE_POLICY.md` + release contract gate;
- RC readiness → dedicated Semantic Solver RC workflow.

The frozen governing rule is:

```text
claim_policy = NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE
```

> **NO PUBLIC CAPABILITY CLAIM WITHOUT A REPRODUCIBLE GATE.**

## 6. Complete RC certification

The real RC workflow requires all of the following to pass together:

1. freeze-manifest generation;
2. v0.41/v0.47/v0.48 upgrade/replay compatibility;
3. cross-run conformance;
4. semantic/adversarial certification;
5. native SAT/CP-SAT/MILP conformance;
6. CVXPY/PuLP modeling conformance;
7. advanced solver conformance;
8. exact cross-backend overlap certification;
9. benchmark workload/replay validation;
10. public claim-gate audit;
11. project-wide Apache-2.0 policy freeze.

The dedicated `.github/workflows/rc.yml` installs the real optimization stack and executes these checks on Python 3.13 in addition to the ordinary CI, Formal Assurance, Optimization Backends, and Cross-Run Knowledge workflows.

## 7. Existing authority boundaries remain unchanged

v0.49 adds assurance surfaces only.

```text
solver output       = Evidence
search state        = performance state
benchmark timing    = measurement
prior-run knowledge = foreign Evidence until local admission
SII utility         = resource economics
truth/authority     = existing AASM policy boundary only
```

The v0.47 law remains intact:

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

The v0.48 law remains intact:

```text
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY.
```

The project-wide licensing declaration remains `Apache-2.0` through `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
