# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, native solvers, governed memory, and cross-run knowledge.**

## Current release — v0.50.0

**Proof-Carrying Solver Claims**

**Next release:** v0.51.0 — Governed Solution Pools & Complete Enumeration

AASM is an event-sourced control plane for work that must survive retries, crashes, competing agents, changing evidence, external solvers, long-lived memory, and prior-run knowledge **without allowing any of those inputs to silently become authority or truth**.

v0.50 adds proof-carrying solver claims as a thin layer over the v0.49 release-candidate runtime. Solver status remains Evidence; only an independent passing checker can label an exact-bound claim `PROOF_CERTIFIED`, and that certificate still does not become policy or truth authority.

AASM's declared project license is **Apache License, Version 2.0 (`Apache-2.0`) across the project**. To the extent AASM has the necessary relicensing rights, prior AASM versions—including versions first distributed under MIT—are **also offered under Apache-2.0**. Previously granted MIT permissions remain valid for their recipients, but prior AASM versions are not designated MIT-only. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`LICENSE_POLICY.md`](LICENSE_POLICY.md).

### Current release contracts

```text
package / public surface: 0.50.0
aasm.adoption.v1 / 0.26.0
aasm.solver.proof-certificate.v1 / 0.1.0
aasm.semantic.solver.rc.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.knowledge.cross-run.admission.v1 / 0.1.0
aasm.principal.cross-run-map.v1 / 0.1.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
license: Apache-2.0
```

## Why AASM exists

The failure mode AASM targets is architectural: useful reasoning, solver output, memory, cached results, model confidence, or prior-run success gets mistaken for authority.

AASM separates those concerns:

```text
proposal / observation / solver output
                 |
                 v
              Evidence
                 |
        validation / policy
                 |
        authority boundary
                 |
      durable state / truth
```

Performance state is allowed to improve performance. It is not allowed to redefine correctness.

## v0.50 — Proof-Carrying Solver Claims

The governing distinction is:

```text
SOLVER STATUS != PROOF GRADE
SOLVER_VALIDATED = ordinary independently validated solver Evidence
PROOF_CERTIFIED  = exact-bound claim + proof artifact + independent checker PASS
```

The v0.50 contract is `aasm.solver.proof-certificate.v1 / 0.1.0`. Its first checker, `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0`, exhaustively verifies bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims. Continuous domains, unsupported claim kinds, and proof spaces beyond the configured finite-domain budget remain explicitly `UNSUPPORTED`; they are never mislabeled as failed proofs or silently promoted.

Claims, proof artifacts, and certificates are durable through the existing AASM Evidence/event history. A passing certificate has `certificate_authority = EVIDENCE_ONLY` and `truth_authority = EXISTING_AASM_POLICY_ONLY`.

```text
proof failure       -> no PROOF_CERTIFIED
proof unsupported   -> no PROOF_CERTIFIED
solver self-check   -> no PROOF_CERTIFIED
independent PASS    -> PROOF_CERTIFIED Evidence only
```

Public CLI:

```bash
aasm solver-proof-contract
aasm solver-proof-conformance
```

See `docs/PROOF_CARRYING_SOLVER_CLAIMS.md` for exact scope and non-claims.

## v0.49 — Semantic Solver Release Candidate

The RC contract is:

```text
aasm.semantic.solver.rc.v1 / 0.1.0
stability        = RELEASE_CANDIDATE
runtime_extension = THIN_V48_COMPOSITION_NO_NEW_KERNEL
compatibility_floor exercised = v0.41
```

The current runtime is:

```text
SemanticSolverRCRuntimeMixin
          +
runtime_v48.AASMEngine
```

### Public contract freeze

`aasm semantic-solver-rc-freeze` emits and fingerprints the current public compatibility surface:

- contract IDs and versions;
- engine methods;
- CLI commands;
- public imports;
- inspection surfaces;
- JSON schemas;
- solver/provider identities;
- event-history replay expectation;
- Apache-2.0 + `LICENSE_POLICY.md` identity.

The freeze manifest is a reviewable target for the `0.49.x` line. It does not pretend undocumented private implementation details are permanent APIs.

### Upgrade and replay guarantees exercised by the RC

The dedicated RC fixture creates durable histories with prior released generations and resumes them under v0.49:

```text
v0.41 → v0.49
  events
  memoized state
  governed v0.40 memory

v0.47 → v0.49
  governed SII policy
  durable SII principal binding

v0.48 → v0.49
  admitted cross-run knowledge
  foreign-authority non-inheritance
```

Each fixture must replay to the exact canonical snapshot hash and preserve the representative durable state under test.

### Cross-backend certification

OR-Tools CP-SAT and HiGHS independently solve the same exact discrete optimization model:

```text
x, y ∈ {0,1}
x + y >= 1
minimize x + y
```

Both must return and independently validate optimum `1`.

CaDiCaL independently solves the Boolean feasibility projection:

```text
x OR y
```

The rule is explicit:

```text
AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE
```

Cross-backend agreement is corroborating Evidence. Backend disagreement is not converted into majority truth.

### Benchmark evidence without benchmark theater

The RC measures:

- canonical semantic fingerprint workloads;
- event append + deterministic replay workloads;
- direct native CP-SAT execution when native dependencies are present;
- the equivalent full AASM provider → request → TaskLease → solve → validate → Evidence lifecycle;
- observed orchestration-overhead ratio.

Those measurements are environment-specific evidence. AASM makes **no ungated speedup claim** from them:

```text
MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM
AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS
```

### Public claims must map to real gates

The RC adds:

```text
NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE
```

The claim audit ties major README claims to concrete source/workflow evidence, including Python support, Formal Assurance, Optimization Backends, Cross-Run Knowledge, project-wide Apache licensing, and the Semantic Solver RC gate.

### The RC is a release gate

`.github/workflows/rc.yml` installs the real native optimization/modeling stack and publishes:

```text
aasm/semantic-solver-rc
```

A release now requires the exact current `main` SHA to have all three:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
```

at `success` before publication.

## Core architecture

```text
                           AASM
                            |
                canonical semantic state
                            |
      +----------+-----------+-----------+----------+
      |          |           |           |          |
      v          v           v           v          v
 reasoning    memory       reuse       solvers      SII
      |          |           |           |          |
      |          |       certificate     |       resources
      |          |           |           |          |
      +----------+-----------+-----------+----------+
                            |
                         Evidence
                            |
                    validation / policy
                            |
                    authority boundary
                            |
                       durable state
```

There is one scheduler/TaskLease plane and one durable authority path.

## Native solver portfolio

AASM owns semantic identity, provider admission, leases, provenance, independent validation, Evidence, certified reuse, and authority boundaries. Native solver projects own their optimized inner search loops.

```text
                              AASM
                               |
                    canonical problem identities
                               |
       +---------+--------------+------------+--------------+---------+
       v         v              v            v              v         v
      SAT     CP-SAT           MILP        CONVEX         SMT/FOL    PROOF
       |         |              |            |              |         |
 Kissat /     OR-Tools       HiGHS         CVXPY       Z3 / cvc5   Lean 4
 CaDiCaL      scheduling    warm starts    QP / SOC       Vampire
       |         |              |            |              |         |
       +---------+--------------+------------+--------------+---------+
                               |
                      normalized Evidence
```

### Fast and incremental SAT

- **Kissat** — fast non-incremental Boolean solving.
- **CaDiCaL** — direct SAT plus incremental assumptions, UNSAT cores, conflict/decision budgets, and bounded session reuse.

Learned SAT state is `EPHEMERAL_PERFORMANCE_ONLY`.

### CP-SAT scheduling — OR-Tools

Supports fixed/optional intervals, `NO_OVERLAP`, `CUMULATIVE`, deterministic-time budgets, search-worker controls, and search telemetry.

### MILP — HiGHS

Supports warm starts, MIP gap targets, node limits, primal/dual bounds, gap, node count, and iteration telemetry.

### Convex optimization — CVXPY

Supports governed convex LP/QP/SOC execution, factorized PSD/NSD quadratic objectives, cross terms, and affine SOC constraints with independent AASM validation.

### PuLP

PuLP is compatibility only:

```text
authority        = TRANSLATION_ONLY
solver_execution = NEVER
```

Supported PuLP models become AASM IR and are then routed to native providers.

## Formal verification portfolio

The formal path remains first-class:

- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Vampire** — TPTP first-order theorem proving;
- **Lean 4** — trusted proof-kernel checking.

Formal output is Evidence. Solver agreement is not majority voting. Lean rejection is not automatically a logical refutation.

## Governed SII

SII measures which reasoners create durable utility and allocates discretionary resources accordingly.

It can govern:

- context budget;
- scheduler priority;
- SAT conflicts/decisions;
- CP-SAT deterministic time/workers;
- MILP nodes;
- convex solve time;
- discretionary formal work;
- portfolio width.

Its safety law remains:

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

**Required verification is never reduced** by a reasoner's SII score.

## Cross-Run Knowledge

v0.48 allows useful verified material to move across durable runs without moving source authority.

A `CrossRunKnowledgeEnvelope` records source run/machine/scope, source lineage, content fingerprints, environment/dependencies, verification strength, privacy, freshness, and retention.

```text
authority_transfer = NEVER
```

Receiving-run applicability is validated before local POLICY/CONTROLLER admission.

Foreign semantic content cannot become local semantic memory without receiving-run `AUTHORIZED` reasoning. Cross-run reuse goes through the existing v0.41 `ReuseCandidate` → validation → `ReuseCertificate` path. Source revocation/supersession blocks hot reuse and tombstones materialized memory through governed FORGET operations.

Imported SII reputation remains:

```text
truth_authority              = NONE
resource_entitlement         = NONE
used_by_sii_resource_lease   = false
```

The governing boundary is:

```text
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY.
```

## Installation

Base runtime:

```bash
pip install aasm-runtime
```

Full native optimization/modeling portfolio:

```bash
pip install 'aasm-runtime[optimization]'
```

CVXPY + PuLP modeling only:

```bash
pip install 'aasm-runtime[modeling]'
```

PostgreSQL support:

```bash
pip install 'aasm-runtime[postgres]'
```

## RC CLI

```bash
aasm semantic-solver-rc-contract
aasm semantic-solver-rc-freeze
aasm semantic-solver-rc-upgrade
aasm semantic-solver-rc-cross-backend --real
aasm semantic-solver-rc-benchmark --real --iterations 64
aasm semantic-solver-rc-claim-audit
aasm semantic-solver-rc-certify --real
```

Existing solver/SII/certification CLI remains available, including:

```bash
aasm optimization-conformance --real
aasm modeling-conformance --real
aasm advanced-optimization-conformance --real
aasm cross-run-knowledge-conformance
aasm certify
aasm certify --target sii-preview
```

## Verification

AASM's current release gates include:

- Python 3.11 / 3.12 / 3.13 full test matrices;
- deterministic replay;
- SQLite and PostgreSQL persistence;
- Compose full-stack smoke testing;
- byte-reproducible wheel/sdist builds and clean installation;
- LangGraph and framework-neutral adapter conformance;
- **Optimization Backends** with real native solvers;
- **Cross-Run Knowledge** governance/adversarial tests;
- **Formal Assurance** with bounded TLA+ and Promela/SPIN;
- **Semantic Solver RC** upgrade, cross-backend, benchmark, claim-audit, public CLI, and full real certification;
- **Proof Claims** exact binding, proof applicability, adversarial rejection, public CLI, replay, and conformance; publishes exact-head `aasm/proof-claims`;
- project-wide Apache-2.0 / PEP 639 / `LICENSE` / `NOTICE` / `LICENSE_POLICY.md` release checks;
- exact-head release publication and remote asset byte verification.

## License

AASM is licensed under the **Apache License, Version 2.0** (`Apache-2.0`) as a project-wide declaration. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`LICENSE_POLICY.md`](LICENSE_POLICY.md).

To the extent AASM controls the necessary relicensing rights, **prior AASM versions are also offered under Apache-2.0**, including versions that were first distributed under MIT. Previously granted MIT permissions remain valid for recipients who received those grants; that does not make those prior AASM versions MIT-only.

Third-party material, if any, remains subject to its own applicable terms.

## Roadmap

- v0.35 Semantic Problem Model ✅
- v0.36 Semantic Compiler SDK ✅
- v0.37 Reasoning Artifacts & Epistemic Admission ✅
- v0.38 Dependency Graph & Truth Maintenance ✅
- v0.39 Typed Capability ABI + Z3/cvc5/Vampire/Lean ✅
- v0.40 Hierarchical Memory & Context Projection ✅
- v0.41 Domain-Neutral Solver Loop & Deterministic Reuse ✅
- v0.42 Reference-Domain Stress Tests ✅
- v0.43 Semantic/Adversarial Certification ✅
- v0.44 Heterogeneous Optimization — CaDiCaL / CP-SAT / HiGHS ✅
- v0.45 Convex Optimization & Modeling Adapters — CVXPY / PuLP ✅
- v0.46 Advanced Solver Control & Search Artifacts ✅
- v0.47 Governed Symbiotic Intelligence & Intelligence Economics ✅
- v0.48 Cross-Run Certified Knowledge & Governed Long-Term Memory ✅
- v0.49 Semantic Solver Release Candidate ✅
- **v0.50 Proof-Carrying Solver Claims — current ✅**
- **v0.51 Governed Solution Pools & Complete Enumeration — next**
- v0.52 Lexicographic Multi-Objective & Pareto Solving
- v0.53 Durable Cross-Run Solver Learning
- v0.54 Certified Cross-Solver Exchange & Deterministic Portfolio Racing
- v0.55 Extended Mathematical IR
- v0.56 Proof/Enumeration/Optimization Stress Corpus
- v0.57 Semantic Solver RC2 / Contract Review
- **Beyond v0.57: open-ended AASM research and capability program; no presumed v1.0.**

The v0.50–v0.57 sequence closes the **currently identified semantic-solver gap cluster**. It does not close AASM and does not imply readiness for a stable-major release.

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/PROOF_CARRYING_SOLVER_CLAIMS.md](docs/PROOF_CARRYING_SOLVER_CLAIMS.md), [docs/RELEASE_0.50.md](docs/RELEASE_0.50.md), [docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md](docs/SEMANTIC_SOLVER_RELEASE_CANDIDATE.md), and [LICENSE_POLICY.md](LICENSE_POLICY.md).
