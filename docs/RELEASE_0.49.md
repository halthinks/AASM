# AASM v0.49.0 — Semantic Solver Release Candidate

AASM v0.49 is the first release-candidate freeze of the semantic solver/control stack assembled through v0.48. It adds no new scheduler, reducer, memory store, authority plane, or inner solver kernel.

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
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

## Release-candidate freeze manifest

The RC emits a deterministic freeze manifest over the current public surface:

- public contract IDs and versions;
- engine methods;
- CLI commands;
- public imports;
- inspection surfaces;
- JSON schemas;
- solver/provider identities;
- persistence/replay expectation;
- Apache-2.0 + `LICENSE_POLICY.md` identity.

The manifest is fingerprinted and provides a reviewable compatibility target for the 0.49.x line.

## Upgrade/replay compatibility

The RC creates representative durable histories with older released runtime generations and resumes them under `runtime_v49.AASMEngine`:

```text
v0.41 → v0.49: events + memo + governed memory
v0.47 → v0.49: governed SII policy + principal binding
v0.48 → v0.49: admitted cross-run knowledge + authority non-inheritance
```

Every fixture must reproduce its canonical snapshot under replay and preserve the generation-specific state exercised by the fixture.

## Cross-backend certification

The exact discrete optimization problem

```text
x, y ∈ {0,1}
x + y >= 1
minimize x + y
```

is independently solved through OR-Tools CP-SAT and HiGHS MILP. Both must return and independently validate optimum `1`. CaDiCaL separately solves the Boolean feasibility projection `x OR y`.

Agreement supplies corroborating Evidence. Disagreement does not become majority truth:

```text
cross_backend_rule = AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE
```

## Benchmark evidence

The RC records:

- semantic-fingerprint workload timing;
- event append/replay timing;
- direct native CP-SAT solve timing when native dependencies are installed;
- the corresponding full AASM provider/request/TaskLease/execute/validate/Evidence lifecycle timing;
- observed orchestration-overhead ratio.

These measurements are environment-specific evidence. No speedup claim is inferred from them.

```text
native_solver_claim = AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS
benchmark_policy    = MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM
```

## Claim-to-gate audit

The RC introduces the invariant:

```text
NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE
```

Public claims about Python support, formal assurance, native solvers, cross-run governance, project-wide Apache licensing, and RC readiness are checked against concrete repository files/workflows.

## Dedicated release gate

`.github/workflows/rc.yml` installs the complete real optimization/modeling stack and executes:

- dependency-neutral RC assurance;
- real CaDiCaL / OR-Tools / HiGHS overlap certification;
- full leased-solver benchmark lifecycle;
- complete real optimization/modeling/advanced conformance aggregation;
- v0.41/v0.47/v0.48 replay/upgrade fixtures;
- public RC CLI surfaces;
- claim-gate audit.

It publishes the exact-head status:

```text
aasm/semantic-solver-rc
```

The release workflow now requires **CI + Formal Assurance + Semantic Solver RC** success on the exact current `main` SHA before publishing a version.

## Existing invariants preserved

```text
SEARCH_STATE_NEVER_PROMOTES_TRUTH
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION
REQUIRED VERIFICATION IS NEVER REDUCED BY SII
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY
```

Solver results, benchmark measurements, SII utility, and prior-run knowledge remain evidence/performance/accounting surfaces outside the truth-authority boundary.

## Licensing

AASM remains Apache-2.0 under the project-wide declaration in `LICENSE_POLICY.md`. Prior AASM versions are also offered under Apache-2.0 to the extent AASM has the necessary relicensing rights. Previously granted MIT permissions remain valid for recipients, without designating prior versions MIT-only.
