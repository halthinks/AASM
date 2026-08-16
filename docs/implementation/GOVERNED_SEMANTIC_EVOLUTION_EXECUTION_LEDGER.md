# AASM Governed Semantic Evolution — Execution Ledger

**Status projection date:** 2026-08-16  
**Latest immutable release:** `v0.56.0` at commit `551b2f4780acaeb93384b454f6f474f6ebd1b30e`  
**Current development target:** `0.56.1` on `main`; exact unreleased identity is Git SHA  
**Current adoption contract:** `aasm.adoption.v1 / 0.32.5`  
**Doctrine:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`  
**Physical/distributed reconciliation:** `docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`  
**Physical integration plan:** `docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md`  
**Roadmap:** `ROADMAP.md` and `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`  
**Version/release policy:** `docs/VERSIONING.md`  
**Historical v0.56 work-package release plan:** `docs/roadmaps/V056_CUMULATIVE_RELEASE_DISCIPLINE.md` — retained for provenance, superseded for future package allocation  
**Source lock:** `docs/source_material/SOURCE_LOCK_MANIFEST.md`

This is the canonical mutable progress ledger. It may advance or refine work items, but locked requirements may not disappear. When an item is split, the parent row remains and points to its children.

Package SemVer is not an architecture-progress counter. Historical work-package IDs such as `56.2`, `57.1`, and `60.2` remain stable dependency/provenance identifiers; future work uses named milestone/program IDs and does **not** reserve future package versions.

Dormant or interrupted source code does not advance a row by itself. A row advances only when the relevant contract/runtime/test/gate evidence is deliberately admitted and qualified. A prerequisite must be semantically landed and sufficiently qualified before dependent work relies on it, but it does **not** need to be published as its own package release first.

## Status vocabulary

`SOURCE_LOCKED | DESIGNED | CONTRACT_LANDED | RUNTIME_LANDED | TESTED | GATED | RELEASED | BLOCKED`

- `GATED` means the declared qualification gate has actually executed the capability claims on an exact Git head.
- `RELEASED` means an immutable published package/tag exposes the capability.
- `GATED` does **not** imply `RELEASED`.

## Active execution ledger

| ID | Milestone / historical release | Capability | Status | Primary source requirement | Current code/contracts | Dependencies | Acceptance / adversarial evidence | Claim ceiling | Gate / next action |
|---|---|---|---|---|---|---|---|---|---|
| SRC-001 | cross | Source lock and doctrine | SOURCE_LOCKED | Preserve supplied TextPCB/AASM sources; prevent implementation drift | Whitepaper, canonical roadmap, source-lock manifest; exact source bundle retained separately | released semantic baseline | immutable hashes + precedence/no-overwrite rules | architecture doctrine only | add source revisions explicitly; never silently rewrite locked sources |
| VER-001 | development-identity-policy | Release/development identity separation | GATED | Git SHA, milestone, contract version, and package release must be distinct identity planes | `docs/VERSIONING.md`; `scripts/check_version_policy.py`; `.github/workflows/version-policy.yml`; manual-only release workflow | existing release gates | version-policy workflow passes without package bump; new chronology modules/version bumps rejected | development/release governance only | preserve; consolidate historical chronology gradually |
| 55.1-A | released v0.55.0 | ExternalReference | RELEASED | stable external requirement/decision identity through generated objects | `aasm.external.reference.v1`; schema; semantic evolution runtime | semantic fingerprinting | deterministic round trip + missing identity rejection | identity/provenance only; no truth authority | preserve |
| 55.1-B | released v0.55.0 | ProblemRevision | RELEASED | revision-bound solver/verifier/external semantics | `aasm.problem.revision.v1`; Evidence projection/runtime | 55.1-A | SQLite replay/restart; stale revision rejection | canonical revision identity; no external-state authority claim | preserve/extend |
| 55.1-C | released v0.55.0 | ProblemDelta | RELEASED | deterministic semantic change description | `aasm.problem.delta.v1`; typed truth-change roots | 55.1-B; semantic dependencies | stale-base fencing; semantic-fingerprint checks | declared delta only; no universal domain inference | preserve/extend |
| 55.1-D | released v0.55.0 | Revision transition + durable runtime | RELEASED | crash-safe application and precise invalidation | semantic-evolution runtime over existing Evidence/reducer | 55.1; truth maintenance; effects | restart/idempotent resume/replay/two-host stale writer | no parallel truth table | preserve |
| 55.2-A | released v0.55.0 | Model feature set | RELEASED | fail-closed semantic feature declaration | `aasm.model.feature-set.v1` | 55.1 | exact/approximate admission fixtures | declaration/admission only | preserve |
| 55.2-B | released v0.55.0 | Provider capability manifest | RELEASED | provider feature/status/proof/provenance negotiation | `aasm.provider.capability-manifest.v1` | 55.2-A | missing/approximate capability fail-closed | capability evidence only | preserve; later generalize executor/machine capability semantics |
| 55.2-C | released v0.55.0 | Model admission report | RELEASED | prevent unsupported lowering | `aasm.model.admission.v1` | 55.2-A/B | verifier-only and approximation fixtures | pre-execution semantic admission | preserve |
| 55.3 | released v0.55.0 | Generalized formulation artifact | RELEASED | preserve variable/constraint/objective/source mappings | `aasm.solver.formulation.v1` + certificate/runtime | 55.1/55.2 | mapping completeness/revision fencing/checker | exact identity checker only unless stronger checker exists | preserve |
| 55.3-A | released v0.55.0 | Exact pseudo-Boolean/cardinality IR | RELEASED | richer exact discrete constraints | `src/aasm/discrete_ir.py` | 55.2/55.3 | equivalence/tamper/contradiction fixtures | exact lowering only | preserve |
| 55.3-B | released v0.55.0 | Portable scheduling IR | RELEASED | portable scheduling semantics | `src/aasm/scheduling_ir.py` | 55.2/55.3 | precedence/no-overlap/cumulative validation | representation/validation; complete execution adapter not claimed | preserve |
| 55.3-C | released v0.55.0 | Deterministic quadratic/conic IR | RELEASED | continuous engineering representation | `src/aasm/continuous_ir.py` | 55.2/55.3 | deterministic serialization/feasibility/tolerance binding | structural + assignment validation; no global optimality proof | preserve; later compose with hybrid-state envelopes |
| 55.4 | released v0.55.0 | Shared objective-vector IR | RELEASED | semantic objectives and hard floors | `src/aasm/decision_vector_ir.py` | 55.1–55.3 | hard-floor exclusion/priority fixtures | scalarization none; exact representability required | preserve |
| 55.5 | released v0.55.0 | Portable semantic-evolution archive | RELEASED | portable replay/export without hosted truth | `aasm.semantic-evolution.archive.v1` | 55.1–55.4 | byte-stable round trip/tamper/reducer replay | event history is replay input; snapshot comparison evidence | preserve; foundational for portable-kernel differential replay |
| 56.1 | released v0.56.0 | Solver Outcome v2 | RELEASED | truthful solver termination/incumbent/bound/proof semantics | `solver_outcome_v2.py`; `provider_status_v2.py`; runtime + schemas | 55.2/55.3 | terminal-class corpus; independent incumbent validation; native provider mapping | normalization grants no truth; provider optimal is not independent proof | preserve |
| 56.2 | `execution-profiles-runtime-provenance`; existing 0.56.1 target | Execution profile + runtime provenance | GATED | evidence-grade observed execution configuration | `solver_provenance.py`; `_runtime_v56_provenance.py`; `solver_execution_observation.py`; schemas; active `public_v56` | 55.3; 56.1 | exact-head `aasm/v56-provenance` and cumulative `aasm/v56`; real CaDiCaL/OR-Tools/HiGHS/CVXPY fixtures | provenance alone does not prove reproducibility; unknown thread/config remains unknown | preserve in current coherent release train; no new package version allocated by subsequent work |
| 56.3 | `reproducibility-certification` | Reproducibility certification | SOURCE_LOCKED | truthful semantic/assignment/objective/proof reproduction claims | dormant `reproducibility.py`, `_runtime_v56_reproducibility.py`, and `solver_provenance_v2.py` work exists but is not active/admitted | qualified 56.2 | no active public/gate evidence yet; dormant source is insufficient | none beyond existing provenance ceiling | reconcile dormant v2 provenance with active provenance contract before admission |
| 56.4 | `knowledge-applicability-application` | Generic knowledge applicability/application | SOURCE_LOCKED | applicability-scoped learned constraints beyond solver learning | generalize v0.48/v0.53 mechanisms; no second knowledge store | 55.1; 56.1; solver learning | poisoned/cross-revision/cross-scope reuse corpus required | solver-learning subset already real | design explicit applicability/application contracts |
| 56.5 | `integrated-core-conflict-pipeline` | Integrated core/conflict pipeline | SOURCE_LOCKED | raw → normalized → minimized → independently rechecked requirement core | `conflict_minimization.py` exists as reusable primitive | 55.1; 55.3; 56.1 | irrelevant assumption/core-oracle fixtures | generic minimizer exists; integrated solver/domain pipeline not claimed | integrate after lineage + truthful outcomes |
| 57.1 | `external-machine-supervision` / PR-2A | External machine binding | GATED | supervise an external authoritative state machine without mirroring truth | `aasm.machine.binding.v1`; `aasm.machine.state-observation.v1`; `aasm.machine.external.runtime.v1`; `external_machine.py`; `external_machine_runtime.py`; schemas; active `public_v56` | v0.54 effects; 55.1 revisions; PR-1 | exact-head `aasm/external-machine`; subject/namespace/revision/capability laundering rejection; SQLite replay; binding references cannot mint fact/effect authority | reference/correlation only; no external truth copy, executor invocation, effect authority, or core machine-state mutation | preserve as PR-2A boundary; PR-2B/2C now qualified on top |
| 57.2 | `external-machine-supervision` / PR-2B–2C | Revision-safe transition, state observation, postcondition verification | GATED | expected authoritative pre-state/revision, desired target state, post-effect observation, execution correlation, independently authoritative achieved state | `aasm.machine.transition.v1`; `aasm.machine.transition.runtime.v1`; `aasm.machine.postcondition-verification.v1`; `aasm.machine.postcondition-verification.runtime.v1`; existing v0.54 `EffectIntent`/ownership/reconciliation; active `public_v56` | 57.1; effects; PR-1 | exact-head `aasm/machine-transition`, `aasm/machine-postcondition`, cumulative `aasm/v56`, and full CI; real resource→worker→TaskDemand→TaskLease→ownership→dispatch path; stale prestate/correlation, ACK-without-achievement, non-authoritative observation, mismatch, idempotency, SQLite replay | `SUCCEEDED` is not achieved state; exact canonical equality only; no freshness/calibration/tolerance semantics; no second dispatcher/effect lifecycle or authority minting | preserve; next dependency is PR-3 physical authority/capabilities and PR-4 temporal/identity/calibration semantics |
| 57.3 | `external-machine-supervision` | Artifact revision lineage | DESIGNED | immutable CAD/PCB/CAE/physical outputs | designed `aasm.artifact.revision.v1`; artifact backends exist but canonical lineage contract not active | 55.1; 57.1 | tamper/parent/stale artifact fixtures | artifact existence is not authoritative acceptance | implement canonical artifact lineage |
| 57.4 | `external-machine-supervision` | Entity evolution | DESIGNED | persistent semantic identity across topology/tool/world-model changes | designed `aasm.entity.evolution.v1` | 57.3 | ambiguous mapping blocks hard reuse | none yet | genericize beyond CAD |
| 58.1 | `governed-refinement-verification-planning` | Governed refinement proposal/loop | DESIGNED | solve→verify→diagnose→refine→re-solve without evaluator self-mutation | designed `aasm.refinement.proposal.v1` / `aasm.refinement.loop.v1`; ProblemDelta and Evidence substrates released | 55.1; 56.4; 57.x | stale/self-authorized/no-progress/oscillation attacks | evaluator proposes only; existing authority commits | implement as composition, not new truth/scheduler |
| 58.2 | `governed-refinement-verification-planning` | Verification planning/debt | DESIGNED | multi-fidelity evidence acquisition and unresolved verification obligations | designed `aasm.verification.plan.v1` / `aasm.verification.debt.v1`; resources and verifier ABI exist | resources; verifier ABI; revisions | cheap pass cannot clear stronger obligation | debt is projection, not truth mutation | implement on existing obligations/Evidence/resources |
| 59.1 | `engineering-semantics-production-search` | Quantity/unit/tolerance semantics | DESIGNED | dimensional correctness | designed `aasm.quantity.v1`; current continuous IR has numerical/tolerance policy but not general physical quantity contract | 55.1 | unit/dimension/rounding/tolerance attacks | no generic physical-quantity claim yet | implement reusable quantity contract |
| 59.2 | `engineering-semantics-production-search` | Rule applicability/precedence | DESIGNED | hard floor/hard/policy/preference/advisory semantics | designed `aasm.rule.v1`; hard floors already exist in objective-vector semantics | 55.1; 59.1 | waiver/priority/scope attacks | objective priority cannot override rule authority | implement independently from optimization priority |
| 59.3 | `engineering-semantics-production-search` | Semantic projection/equivalence | DESIGNED | meaningful top-K/diversity/cross-backend equivalence | design exists; semantic fingerprints/projections already used narrowly | 55.1/55.3 | auxiliary differences collapse only under explicit projection | none generic yet | implement shared equivalence contract |
| 59.4 | `engineering-semantics-production-search` | Production lexicographic/Pareto | DESIGNED | scalable objective ordering/frontier truth | extend v0.52 finite reference engine | 55.4; 56.1; 59.3 | exact finite oracle qualifies scalable path | finite exact semantics already released | preserve partial/exact claim levels |
| 59.5 | `engineering-semantics-production-search` | Scalable pools/top-K/diversity | DESIGNED | production alternatives | extend v0.51 pools | 59.3/59.4 | top-K/near-optimal/diverse/restart fixtures | finite completeness currently released | truthful partiality required |
| 59.6 | `engineering-semantics-production-search` | Proof/checker expansion | DESIGNED | SAT proof transport; LP/MILP claims where genuine | extend v0.50 proof plane | 55.3; 56.x | forged/mismatched proof artifacts | provider-specific ceilings | implement only where checker/toolchain supports claim |
| 60.1 | `uncertainty-readiness-conformance` | Uncertainty/scenario/trace semantics | DESIGNED | operating modes, manufacturing variation, transient requirements | designed `aasm.uncertainty.v1`, `aasm.scenario.v1`, `aasm.trace-property.v1` | 55.1; 59.1 | nominal-vs-robust separation | none generic yet | implement explicit uncertainty/trace semantics |
| 60.2 | `uncertainty-readiness-conformance` | Readiness gate | DESIGNED | deterministic explainable completion/release predicate | designed `aasm.readiness.gate.v1` | 57–60 | UNKNOWN/stale/debt/conflict blocks readiness | none generic yet | implement explanation-required predicate |
| 60.3 | `uncertainty-readiness-conformance` | Engineering conformance + TextPCB qualification | DESIGNED | generic external-domain kit; TextPCB as demanding consumer | extend adapter-conformance substrate | all prior | realistic TextPCB mock/qualified fixtures | no TextPCB kernel types | qualify only after generic contracts land |
| 61.1 | `cross-capability-stress-corpus` | Permanent adversarial corpus | DESIGNED | proof of public claims under cross-capability attacks | existing specialized adversarial suites provide seed corpus | all | stale/forged/poisoned/UNKNOWN/unsupported/refinement/resource attacks | tests establish only covered properties | make permanent and cumulative |
| 62.1 | `hosted-foundation-review` | Semantic Solver contract + hosted-foundation review | DESIGNED | hosted fabric must consume public semantics without private bypass | architecture review milestone | all | claim-to-gate audit + boundary review | no hosted-semantic bypass claim until review passes | execute after governed semantic evolution is substantially real |

## Reconciliation-discovered physical/distributed seams

These are the durable seams exposed by the Embedded/Physical review. They extend the existing authority, Evidence, resource, effect, revision, knowledge, verification, and refinement planes; they are **not** a separate Embedded AASM product.

| ID | Milestone | Capability | Status | Existing substrate / landed work | Missing semantic elevation / next boundary |
|---|---|---|---|---|---|
| PHY-01 | `physical-authority-capabilities` / PR-3 | Authority domains, leases/epochs, bounded revocable effect capabilities, semantic preemption | DESIGNED | scoped grants/delegation/deny/expiry; typed capability ABI; effect authority evidence | exclusive authority-domain ownership, epoch freshness, capability non-amplification, explicit preemption/revocation semantics |
| PHY-02 | `authoritative-state-claims` / PR-1 | Desired / predicted / observed / authoritative state separation + fact authority | GATED | `aasm.fact.authority.v1`; `aasm.state.claim.v1`; `aasm.state.authority.runtime.v1`; `state_authority.py`; `state_authority_runtime.py`; schemas; active `public_v56`; existing Evidence + scoped authority only | PR-1 boundary complete: observation/consensus cannot create authority, fact authority grants no effect authority, claims do not mutate core machine state; PR-2 external-machine semantics are now qualified on top |
| PHY-03 | `postcondition-verification` / PR-2 | Command ≠ achievement; machine binding, transition attempt, correlated observation and postcondition verifier | GATED | `aasm.machine.binding.v1`; `aasm.machine.state-observation.v1`; `aasm.machine.transition.v1`; `aasm.machine.postcondition-verification.v1`; their runtime mixins/schemas; existing v0.54 EffectIntent/Ownership/Reconciliation/UNKNOWN; active `public_v56` | PR-2 boundary complete: successful governed dispatch/ACK cannot establish achieved state; verification requires correlated post-effect observation plus independently authoritative state; exact equality only; PR-4 owns freshness/clock/calibration/tolerance semantics |
| PHY-04 | `temporal-causal-semantics` / PR-4 | sequence, causal relation, leases/deadlines, observation age, clock quality | DESIGNED | event order, timestamps, lease expiration in existing subsystems | explicit causal/partial-order contract; monotonic device epochs; clock-quality/freshness semantics |
| PHY-05 | `physical-identity-trust` / PR-4 | device/component identity, calibration lifecycle, trust boundary, attestation | DESIGNED | external refs, environment fingerprints, measurement authority, runtime provenance | physical assembly/sensor/calibration identity; validity ranges/expiry; trust claims; secure-boot/firmware attestation hooks |
| PHY-06 | `degraded-autonomy-safety` / PR-5 | degraded modes, safety envelopes, semantic preemption, hybrid discrete/continuous guards | DESIGNED | machine states/obligations, continuous IR, effects, scoped authority | degradation policy, continuous safety envelope, hybrid state contract, emergency/local authority rules |
| PHY-07 | `observation-epistemics` / PR-4 | observation lifecycle, fusion, source independence, epistemic containment | DESIGNED | Evidence, measurement authority, proof/evidence grades, no-voting solver doctrine, PR-1 observed/authoritative split | raw→calibrated→derived/fused lifecycle; fusion contract; no authority laundering across transformations |
| PHY-08 | `epistemic-risk-obligations` / PR-5 | assumptions, epistemic debt, risk/hazards, irreversibility, pre/post obligations | DESIGNED | assumptions/reasoning artifacts, semantic dependencies, verification debt design, `EffectSpec.reversible`/compensation | generalized debt propagation, hazard/risk envelope, irreversible-action evidence escalation, obligation phase taxonomy |
| PHY-09 | `governed-experiments` / PR-6 | experiment contract and information-value evidence acquisition | DESIGNED | refinement design, resources, Evidence, verifier planning | hypothesis/control/measurement/procedure contract; experiment selection under safety/evidence/resource constraints |
| PHY-10 | `portable-kernel-machine-compiler` / PR-7 | language-neutral kernel semantics, stable machine IR, differential replay, Rust std/no_std | DESIGNED | portable semantic archive, typed IRs, deterministic fingerprints, formal models | kernel boundary independent of Python/DB/OS; canonical machine IR; Python/Rust conformance oracle; bounded no_std profile |
| PHY-11 | `embedded-realtime-qualification` / PR-8 | embedded-hal-style executor traits, RTIC mapping, SIM→SIL→HIL→physical qualification, safety profile | DESIGNED | provider/capability manifests, effects, resources, adapter conformance | embedded executor profile, timing contracts, interrupt/event bridge, qualification-level Evidence binding, safety-development restrictions |

## Verified immutable release evidence

### v0.55.0

Release commit: `dd9360858be8755a5639162a7d388d867c1b01e6`  
Tag: `v0.55.0`  
GitHub release workflow: `31912974049` — **SUCCESS**

The release passed the exact-head CI/formal/semantic-solver/proof/solution-pool/optimization/scoped-authority/solver-learning/v0.54-parent/v0.55 gates, reproducible wheel/sdist build, clean install, immutable tag targeting, and remote asset SHA-256 verification.

### v0.56.0 — work package 56.1

Release commit: `551b2f4780acaeb93384b454f6f474f6ebd1b30e`  
Tag: `v0.56.0`  
GitHub release workflow: `31916382216` — **SUCCESS**

The release passed the exact-head inherited gates plus `aasm/v56`, reproducible package build, PostgreSQL/Compose/scopes/adapter/LangGraph integration, clean-install public contract exercise, immutable tag/release creation, and remote asset byte/SHA-256 verification.

This immutable release completes **56.1 Solver Outcome v2**. It does not imply release of 56.2, PR-1, or later work.

## Current development qualification evidence

### PR-1 / PHY-02 qualification

A post-PR-1 exact-head qualification snapshot was captured on development commit:

```text
04b8f3325c1698b3fb7b24421636ee9380fecc2a
```

The direct commit-status contexts were all **success** on that exact head, including full CI, formal assurance, semantic solver RC, v0.54/v0.55 parent gates, cumulative v0.56, provenance, and state authority.

The dedicated state-authority qualification exercised contract/source checks, schema validation, authority-denial behavior, no-consensus-authority, expiry/revocation, source-principal impersonation, namespace/revision laundering, no core-machine-state mutation, SQLite restart, and exact replay.

This evidence qualifies PR-1 / PHY-02 as **GATED**, not **RELEASED**.

### PR-2 / 57.1–57.2 / PHY-03 qualification

The complete external-machine supervision chain was qualified on exact development head:

```text
c3f68539bc19b189b42cb8d67b8f2c98a519fe22
```

The following direct commit-status contexts were all **success** on that exact head:

- `aasm/ci-summary`
- `aasm/formal-assurance`
- `aasm/semantic-solver-rc`
- `aasm/proof-claims`
- `aasm/solution-pools`
- `aasm/optimization`
- `aasm/scoped-authority`
- `aasm/solver-learning`
- `aasm/v54`
- `aasm/v55`
- `aasm/v56`
- `aasm/v56-provenance`
- `aasm/state-authority`
- `aasm/external-machine`
- `aasm/machine-transition`
- `aasm/machine-postcondition`

The generic CI matrix passed Python 3.11, 3.12, and 3.13, reproducible wheel smoke, PostgreSQL integration, Compose full-stack smoke, hierarchical scopes, LangGraph integration, and adapter conformance.

The PR-2 qualification specifically proved:

- external machine binding is reference/correlation only and cannot mint fact or effect authority;
- machine observations require already-durable PR-1 `OBSERVED` claims and exact binding/revision/subject/namespace agreement;
- transition proposals lower into the existing v0.54 `propose_effect()` / `EffectIntent` path and cannot authorize or dispatch effects themselves;
- a genuine external-effect attempt uses the existing resource → worker → `TaskDemand` → active `TaskLease` → ownership → dispatch path;
- `EffectStatus.SUCCEEDED` and executor/ACK success cannot establish achieved external state;
- postcondition observations must correlate to the exact existing `EffectRecord.execution_id`;
- achieved state must already be an independently admitted PR-1 `AUTHORITATIVE` claim derived from the supplied correlated observation;
- exact match produces `VERIFIED`, mismatch produces durable `MISMATCH` Evidence, and neither mutates the existing effect outcome or authoritative state;
- `UNKNOWN` remains exclusively on the existing effect reconciliation path;
- SQLite restart/replay and idempotent verification are preserved;
- no parallel dispatcher, effect lifecycle, truth table, or authority evaluator was introduced.

This evidence qualifies **57.1 / PR-2A**, **57.2 / PR-2B–2C**, and **PHY-03 / PR-2** as **GATED**, not **RELEASED**.

## Immediate builder queue

1. Keep `v0.56.0` / `551b2f47…` as the immutable published boundary. Do not publish 0.56.1 automatically.
2. Preserve PR-1 / PHY-02 and PR-2 / PHY-03 claim ceilings; do not widen state claims, bindings, transition proposals, observations, or postcondition verification into actuator authority.
3. Begin **PR-3 / PHY-01 — physical authority + bounded effect capabilities** on top of existing scoped authority and the existing Effect authorization/execution path. Do **not** build a second authority evaluator or dispatcher.
4. PR-3A: land a stable `AuthorityDomain` contract that names the bounded physical/effect authority namespace without granting authority by existence.
5. PR-3B: land exclusive/revocable `AuthorityLease` semantics with explicit holder, workspace/scope/domain, authority epoch/generation, validity interval, and durable evidence/replay.
6. PR-3C/3D: add authority epoch freshness and bounded effect capability semantics; stale epochs and out-of-bounds capability use must fail closed.
7. PR-3E/3F/3G: delegation must never amplify authority; stale-command fencing and revocation/preemption must be explicit and replayable.
8. PR-3H: integrate those contracts into the **existing** `authorize_effect` / `execute_effect` path so physical-effect authority is checked without replacing v0.54 ownership, TaskLease, resource governance, or reconciliation.
9. After PR-3 is qualified, proceed to PR-4 temporal/causal/physical-identity/calibration/observation-epistemics semantics; do not smuggle those semantics into PR-3.
10. Reconcile dormant reproducibility/provenance-v2 source separately before any 56.3 admission; dormant code remains non-authoritative.
11. Keep TextPCB as a demanding consumer/conformance target; do not move TextPCB-specific types into the kernel.

## Completion discipline

A row advances to `TESTED` only with reproducible tests. It advances to `GATED` only when the declared gate executes those claims on an exact Git head. It advances to `RELEASED` only when an immutable published package/tag exposes the capability without exceeding the evidence.

Development may continue from a sufficiently qualified prerequisite without forcing an intermediate package publication. Package SemVer is assigned only at a deliberate coherent release boundary under `docs/VERSIONING.md`.
