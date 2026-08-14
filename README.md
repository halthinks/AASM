# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, native solvers, and governed knowledge.**

## Current release — v0.48.0

**Cross-Run Certified Knowledge & Governed Long-Term Memory**

**Next release:** v0.49.0 — Semantic Solver Release Candidate

AASM is an event-sourced control plane for work that must survive retries, crashes, competing agents, changing evidence, external solvers, long-lived memory, and prior-run knowledge **without allowing any of those inputs to silently become authority or truth**.

The active project/distribution license is **Apache License, Version 2.0 (`Apache-2.0`)**. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). The already-published `v0.47.0` artifact remains historically MIT licensed.

### Current release contracts

```text
package / public surface: 0.48.0
aasm.adoption.v1 / 0.24.0
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

## The architecture

```text
                         model / human / solver
                                  |
                                  v
                            proposal / work
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
             reasoning Evidence          solver portfolio
                    |               Kissat / CaDiCaL / CP-SAT
                    |               HiGHS / CVXPY / Z3 / cvc5
                    |                    Vampire / Lean 4
                    |                           |
                    v                           v
             AASM validation             normalized Evidence
                    |                           |
                    +-------------+-------------+
                                  |
                                  v
                     policy / authority boundary
                                  |
                +-----------------+------------------+
                |                 |                  |
                v                 v                  v
          governed memory     certified reuse     durable truth
                |                 |                  |
                +--------+--------+                  |
                         |                           |
                         v                           |
                cross-run knowledge                 |
                         |                           |
              receiving-run admission               |
                         +---------------------------+
```

AASM's operating rule is intentionally asymmetric:

> **Intelligence, solvers, memory, and prior runs may propose useful evidence. Only the receiving AASM authority path determines what becomes locally admissible, reusable, durable, or true.**

---

## v0.48 — Cross-Run Certified Knowledge

AASM can now carry useful knowledge from one durable run into another without carrying the source run's authority with it.

### Immutable knowledge envelopes

A `CrossRunKnowledgeEnvelope` fingerprints:

- source run, machine, and scope;
- source memory, Evidence, and reasoning-artifact lineage;
- exact source fingerprints;
- content;
- declared environment and dependency compatibility;
- verification strength;
- target receiving scopes;
- privacy principal and privacy level;
- freshness and retention policy;
- source authority provenance.

Every envelope fixes:

```text
authority_transfer = NEVER
```

Source authority is useful provenance. It is **not** a receiving-run credential.

### Receiving-run admission

Before a foreign envelope can even be proposed for admission, AASM checks:

1. the source run is actually foreign;
2. the requested receiving scope is allowed;
3. USER/AGENT privacy matches the receiving principal;
4. a declared environment fingerprint matches;
5. declared dependency fingerprints are available;
6. freshness has not expired;
7. retention has not expired;
8. verification strength satisfies the receiving requirement;
9. source authority will not be inherited.

A successful check produces a `CrossRunAdmissionCertificate` containing the receiving validator ID and version. That certificate **still does not admit the knowledge by itself**.

The durable path is:

```text
CrossRunKnowledgeEnvelope
          |
          v
receiving validator
          |
CrossRunAdmissionCertificate
          |
          v
DecisionRecord(PROPOSED)
          |
POLICY / CONTROLLER
          |
      Obligation
          |
       worker
          |
foreign knowledge Evidence
```

### Foreign semantic truth does not become local truth

An admitted foreign envelope is receiving-run Evidence.

For `SEMANTIC` knowledge, AASM refuses local semantic-memory materialization unless the receiving run supplies local reasoning artifacts already in `AUTHORIZED` state. Materialization then uses the ordinary v0.40 memory operation and still requires local POLICY/CONTROLLER authorization and commit.

That boundary is deliberate:

```text
FOREIGN SEMANTIC CONTENT
        !=
LOCAL AUTHORIZED SEMANTIC MEMORY
```

### Cross-run reuse uses the existing reuse plane

v0.48 does **not** create a second cross-run cache.

A foreign result may be registered as an ordinary v0.41 `ReuseCandidate`. It must pass the same existing applicability checks and receive the same existing `ReuseCertificate` before execution can be skipped.

The current cross-run path starts conservatively with exact semantic-payload equality and preserves v0.41's exact verification-strength rule. A `CHECKED_CERTIFICATE` result is not silently downcast into a `SOLVER_VERDICT` request merely to obtain a cache hit.

When a cross-run result is reusable, the normal reuse certificate also records:

- source run ID;
- receiving run ID;
- envelope ID and fingerprint;
- admission validator ID/version;
- `authority_inherited = false`.

### Revocation and supersession are operational

A source run can emit a signed/authenticated-out-of-band revocation or supersession signal. The envelope format itself is not claimed to authenticate untrusted transport; receiving POLICY/CONTROLLER still admits the matching signal.

Once admitted, v0.48 does more than change a status badge:

- the envelope becomes `REVOKED` or `SUPERSEDED`;
- an already-hot cross-run reuse candidate is blocked before reuse certification can be used;
- locally materialized memories tied to that envelope are tombstoned through the existing v0.40 `FORGET` decision → authorization → commit path;
- historical provenance remains append-only.

### Stable cross-run principal identity

AASM can explicitly bind:

```text
(source_run_id, source_principal_id) -> local_principal_id
```

The mapping is POLICY/CONTROLLER admitted and fixes:

```text
authority_transfer            = NEVER
resource_entitlement_transfer = NEVER
```

Stable source identities cannot silently rebind to another local principal.

### Cross-run SII reputation is accounting, not privilege

An `SII_REPUTATION` envelope must name the exact source principal and match the admitted stable principal map.

Imported reputation is recorded as a separate reference-accounting surface:

```text
truth_authority              = NONE
resource_entitlement         = NONE
used_by_sii_resource_lease   = false
accounting_plane             = CROSS_RUN_REFERENCE_ONLY
```

So historical performance may be inspected without turning reputation into a local authority credential or automatic compute allocation.

---

## Governed SII — v0.47

SII answers a different question from AASM truth maintenance:

> **Which intelligence is worth spending more compute on next?**

The governed SII contract is `aasm.sii.v1 / 0.3.0`, stability `GOVERNED_ENFORCED`.

It provides:

- durable `SIIPrincipalBinding` records;
- measurement authority resolved from durable AASM identity rather than caller assertion;
- self-measurement rejection;
- versioned `SIIScoringPolicy` objects;
- bounded performance windows;
- real `GovernedResourceLease` enforcement over context, scheduler priority, SAT budgets, CP-SAT time/workers, MILP nodes, convex time, and discretionary formal work.

The safety laws remain:

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

**Required verification is never reduced** because a reasoner has a low or high SII score.

---

## Native solver portfolio

AASM owns problem identity, provider admission, scheduling, TaskLease provenance, Evidence, validation, reuse, and authority boundaries. Native projects own their optimized inner solving loops.

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
                               |
                 validation / certification / reuse
```

### SAT

- **Kissat** — fast non-incremental Boolean solving through PySAT's dedicated `Kissat404` binding.
- **CaDiCaL** — direct SAT plus incremental assumptions, UNSAT cores, conflict/decision budgets, and bounded session reuse.

Learned SAT state remains `EPHEMERAL_PERFORMANCE_ONLY`; deleting it changes speed, not truth.

### CP-SAT scheduling — OR-Tools

`solver.cp_sat.scheduling@0.1.0` supports fixed/optional intervals, `NO_OVERLAP`, `CUMULATIVE`, deterministic time, search-worker controls, conflicts/branches, and scheduling validation.

### MILP — HiGHS

`solver.milp.advanced@0.1.0` supports warm starts, node limits, MIP gap targets, primal/dual bounds, gap, node count, and iteration telemetry.

### Convex — CVXPY

`solver.convex.advanced@0.1.0` supports factorized PSD/NSD quadratic objectives, cross terms, and affine second-order cone constraints. AASM independently rechecks canonical feasibility/objective values before Evidence admission.

### PuLP

PuLP remains a compatibility importer only:

```text
authority       = TRANSLATION_ONLY
solver_execution = NEVER
```

Supported models become AASM IR and are then routed to native providers such as HiGHS.

---

## Formal verification portfolio

The existing v0.39 formal path remains first-class:

- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Vampire** — TPTP first-order theorem proving;
- **Lean 4** — trusted proof-kernel checking.

Formal output is Evidence. Solver agreement is not majority voting. Lean rejection is not automatically a logical refutation. No solver result bypasses AASM's authority boundary.

---

## One scheduler, one authority path

Neither solver extensions, SII, nor cross-run knowledge create parallel execution authority.

```text
canonical work / admitted knowledge
          |
Capability / Decision contract
          |
POLICY / CONTROLLER admission
          |
Resource / Obligation
          |
TaskDemand / TaskLease where execution is needed
          |
execution / Evidence
          |
validation
          |
optional certified reuse / epistemic admission
```

---

## Installation

Base runtime:

```bash
pip install aasm-runtime
```

Full native optimization/modeling portfolio:

```bash
pip install 'aasm-runtime[optimization]'
```

CVXPY + PuLP modeling surfaces only:

```bash
pip install 'aasm-runtime[modeling]'
```

PostgreSQL integration:

```bash
pip install 'aasm-runtime[postgres]'
```

---

## CLI

```bash
# v0.48 cross-run knowledge
aasm cross-run-knowledge-contract
aasm cross-run-knowledge-conformance

# v0.47 governed SII
aasm sii-contract
aasm sii-governance-contract
aasm sii-default-scoring-policy
aasm certification-contract
aasm certify
aasm certify --target sii-preview

# v0.46 advanced solver control
aasm advanced-optimization-contract
aasm advanced-optimization-blueprint
aasm advanced-optimization-conformance --real

# v0.45 modeling
aasm convex-optimization-contract
aasm pulp-adapter-contract
aasm modeling-conformance --real

# v0.44 native portfolio
aasm optimization-contract
aasm optimization-blueprint
aasm optimization-conformance --real
```

---

## Verification

The repository independently validates AASM through:

- Python 3.11 / 3.12 / 3.13 full test matrices;
- deterministic replay;
- SQLite and PostgreSQL persistence;
- Compose full-stack smoke testing;
- byte-reproducible wheel/sdist builds and clean install;
- Apache-2.0 PEP 639 / `LICENSE` / `NOTICE` release checks;
- LangGraph and framework-neutral adapter conformance;
- **Optimization Backends** real native solver workflow;
- **Cross-Run Knowledge** admission/revocation/privacy/reuse/SII-separation workflow;
- bounded TLA+ models;
- Promela/SPIN models;
- semantic/adversarial certification;
- exact-head release gating and remote release-asset byte verification.

v0.48 adds formal invariants including:

```text
ForeignAuthorityNeverInherited
AdmissionRequiredBeforeMaterialization
AdmissionRequiredBeforeReuse
RevocationBlocksReuse
RevocationInvalidatesMaterializedMemory
PrivateKnowledgeNeverLeaksAcrossPrincipal
ReputationNeverGrantsAuthority
ReputationNeverGrantsResourceEntitlement
```

---

## License

AASM v0.47.1 and later source releases are licensed under the **Apache License, Version 2.0** (`Apache-2.0`). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

The already-published `v0.47.0` release remains under the MIT License that applied to that artifact when it was published.

---

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
- v0.47.1 Apache-2.0 License Transition ✅
- **v0.48 Cross-Run Certified Knowledge & Governed Long-Term Memory — current ✅**
- **v0.49 Semantic Solver Release Candidate — next**

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/CROSS_RUN_CERTIFIED_KNOWLEDGE.md](docs/CROSS_RUN_CERTIFIED_KNOWLEDGE.md), [docs/RELEASE_0.48.md](docs/RELEASE_0.48.md), [docs/SII_GOVERNED_ECONOMICS.md](docs/SII_GOVERNED_ECONOMICS.md), and [docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md](docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md).
