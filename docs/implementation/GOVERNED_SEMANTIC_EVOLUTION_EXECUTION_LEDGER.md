# AASM Governed Semantic Evolution — Execution Ledger

**Status projection date:** 2026-08-15  
**Latest immutable release:** `v0.56.0` at commit `551b2f4780acaeb93384b454f6f474f6ebd1b30e`  
**Current development target:** `0.56.1` on `main`; exact unreleased identity is Git SHA  
**Doctrine:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`  
**Roadmap:** `ROADMAP.md` and `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`  
**Version/release policy:** `docs/VERSIONING.md`  
**Historical v0.56 work-package release plan:** `docs/roadmaps/V056_CUMULATIVE_RELEASE_DISCIPLINE.md` — retained for provenance, superseded for future package allocation  
**Source lock:** `docs/source_material/SOURCE_LOCK_MANIFEST.md`

This is the canonical mutable progress ledger. It may advance or refine work items, but locked requirements may not disappear. When an item is split, the parent row remains and points to its children.

Package SemVer is no longer used as an architecture-progress counter. Historical work-package IDs such as `56.2`, `57.1`, and `60.2` remain stable dependency/provenance identifiers; future rows use named milestone identity and do **not** reserve future package versions.

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
| VER-001 | development-identity-policy | Release/development identity separation | CONTRACT_LANDED | Git SHA, milestone, contract version, and package release must be distinct identity planes | `docs/VERSIONING.md`; `scripts/check_version_policy.py`; `.github/workflows/version-policy.yml`; manual-only release workflow | existing release gates | no package bump for policy work; new chronology modules/version bumps rejected by policy gate | development/release governance only | allow gate to requalify current exact head; shrink legacy chronology over time, never mass rename |
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
| 55.5 | released v0.55.0 | Portable semantic-evolution archive | RELEASED | portable replay/export without hosted truth | `aasm.semantic-evolution.archive.v1` | 55.1–55.4 | byte-stable round trip/tamper/reducer replay | event history is replay input; snapshot comparison evidence | preserve; foundational for portable kernel differential replay |
| 56.1 | released v0.56.0 | Solver Outcome v2 | RELEASED | truthful solver termination/incumbent/bound/proof semantics | `solver_outcome_v2.py`; `provider_status_v2.py`; runtime + schemas | 55.2/55.3 | terminal-class corpus; independent incumbent validation; native provider mapping | normalization grants no truth; provider optimal is not independent proof | preserve |
| 56.2 | `execution-profiles-runtime-provenance`; existing 0.56.1 target | Execution profile + runtime provenance | GATED | evidence-grade observed execution configuration | `solver_provenance.py`; `_runtime_v56_provenance.py`; `solver_execution_observation.py`; schemas; active `public_v56` | 55.3; 56.1 | exact-head `aasm/v56-provenance` and cumulative `aasm/v56` passed on `99b379a…`; real CaDiCaL/OR-Tools/HiGHS/CVXPY fixtures | provenance alone does not prove reproducibility; unknown thread/config remains unknown | keep in current coherent release train; requalify current head; do not allocate another version because subsequent work begins |
| 56.3 | `reproducibility-certification` | Reproducibility certification | SOURCE_LOCKED | truthful semantic/assignment/objective/proof reproduction claims | dormant `reproducibility.py`, `_runtime_v56_reproducibility.py`, and `solver_provenance_v2.py` work exists but is not active/admitted | qualified 56.2 | no active public/gate evidence yet; dormant source is insufficient | none beyond existing provenance ceiling | reconcile dormant v2 provenance with active provenance contract before admission; no package publication prerequisite |
| 56.4 | `knowledge-applicability-application` | Generic knowledge applicability/application | SOURCE_LOCKED | applicability-scoped learned constraints beyond solver learning | generalize v0.48/v0.53 mechanisms; no second knowledge store | 55.1; 56.1; solver learning | poisoned/cross-revision/cross-scope reuse corpus required | solver-learning subset already real | design explicit applicability/application contracts |
| 56.5 | `integrated-core-conflict-pipeline` | Integrated core/conflict pipeline | SOURCE_LOCKED | raw → normalized → minimized → independently rechecked requirement core | `conflict_minimization.py` exists as reusable primitive | 55.1; 55.3; 56.1 | irrelevant assumption/core-oracle fixtures | generic minimizer exists; integrated solver/domain pipeline not claimed | integrate after lineage + truthful outcomes |
| 57.1 | `external-machine-supervision` | External machine binding | DESIGNED | supervise an external authoritative state machine without mirroring truth | contract designed in canonical whitepaper as `aasm.machine.binding.v1`; no active implementation found | v0.54 effects; 55.1 revisions | stale observed revision/out-of-band change tests required | none yet | implement over existing effect and Evidence paths |
| 57.2 | `external-machine-supervision` | Revision-safe machine transition + state observation | DESIGNED | expected pre-state/revision, postcondition observation, receipt correlation | designed `aasm.machine.transition.v1` and `aasm.machine.state-observation.v1`; existing `EffectSpec` already has pre/postconditions and v0.54 ownership/reconciliation | 57.1; effects | no call before ownership; stale prestate; ACK-without-achievement; UNKNOWN/reconcile | effect ownership is real; achieved-transition semantics not yet generic | add postcondition verifier; no second effect lifecycle |
| 57.3 | `external-machine-supervision` | Artifact revision lineage | DESIGNED | immutable CAD/PCB/CAE/physical outputs | designed `aasm.artifact.revision.v1`; artifact backends exist but canonical lineage contract not active | 55.1; 57.1 | tamper/parent/stale artifact fixtures | artifact existence is not authoritative acceptance | implement canonical artifact lineage |
| 57.4 | `external-machine-supervision` | Entity evolution | DESIGNED | persistent semantic identity across topology/tool/world-model changes | designed `aasm.entity.evolution.v1` | 57.3 | ambiguous mapping blocks hard reuse | none yet | genericize beyond CAD |
| 58.1 | `governed-refinement-verification-planning` | Governed refinement proposal/loop | DESIGNED | solve→verify→diagnose→refine→re-solve without evaluator self-mutation | designed `aasm.refinement.proposal.v1` / `aasm.refinement.loop.v1`; ProblemDelta and Evidence substrates released | 55.1; 56.4; 57.x | stale/self-authorized/no-progress/oscillation attacks | evaluator proposes only; existing authority commits | implement as composition, not new truth/scheduler |
| 58.2 | `governed-refinement-verification-planning` | Verification planning/debt | DESIGNED | multi-fidelity evidence acquisition and unresolved verification obligations | designed `aasm.verification.plan.v1` / `aasm.verification.debt.v1`; resources and verifier ABI exist | resources; verifier ABI; revisions | cheap pass cannot clear stronger obligation | debt is projection, not truth mutation | implement on existing obligations/Evidence/resources |
| 59.1 | `engineering-semantics-production-search` | Quantity/unit/tolerance semantics | DESIGNED | dimensional correctness | designed `aasm.quantity.v1`; current continuous IR has numerical/tolerance policy but not general physical quantity contract | 55.1 | unit/dimension/rounding/tolerance attacks | no generic physical-quantity claim yet | implement reusable quantity contract |
| 59.2 | `engineering-semantics-production-search` | Rule applicability/precedence | DESIGNED | hard floor/hard/policy/preference/advisory semantics | designed `aasm.rule.v1`; hard floors already exist in objective-vector semantics | 55.1; 59.1 | waiver/priority/scope attacks | objective priority cannot override rule authority | implement independently from optimization priority |
| 59.3 | `engineering-semantics-production-search` | Semantic projection/equivalence | DESIGNED | meaningful top-K/diversity/cross-backend equivalence | design exists; semantic fingerprints/projections already used narrowly | 55.1/55.3 | auxiliary differences must collapse only under explicit projection | none generic yet | implement shared equivalence contract |
| 59.4 | `engineering-semantics-production-search` | Production lexicographic/Pareto | DESIGNED | scalable objective ordering/frontier truth | extend v0.52 finite reference engine | 55.4; 56.1; 59.3 | exact finite oracle qualifies scalable path | finite exact semantics already released | preserve partial/exact claim levels |
| 59.5 | `engineering-semantics-production-search` | Scalable pools/top-K/diversity | DESIGNED | production alternatives | extend v0.51 pools | 59.3/59.4 | top-K/near-optimal/diverse/restart fixtures | finite completeness currently released | truthful partiality required |
| 59.6 | `engineering-semantics-production-search` | Proof/checker expansion | DESIGNED | SAT proof transport; LP/MILP claims where genuine | extend v0.50 proof plane | 55.3; 56.x | forged/mismatched proof artifacts | provider-specific ceilings | implement only where checker/toolchain supports claim |
| 60.1 | `uncertainty-readiness-conformance` | Uncertainty/scenario/trace semantics | DESIGNED | operating modes, manufacturing variation, transient requirements | designed `aasm.uncertainty.v1`, `aasm.scenario.v1`, `aasm.trace-property.v1` | 55.1; 59.1 | nominal-vs-robust separation | none generic yet | implement explicit uncertainty/trace semantics |
| 60.2 | `uncertainty-readiness-conformance` | Readiness gate | DESIGNED | deterministic explainable completion/release predicate | designed `aasm.readiness.gate.v1` | 57–60 | UNKNOWN/stale/debt/conflict blocks readiness | none generic yet | implement explanation-required predicate |
| 60.3 | `uncertainty-readiness-conformance` | Engineering conformance + TextPCB qualification | DESIGNED | generic external-domain kit; TextPCB as demanding consumer | extend adapter-conformance substrate | all prior | realistic TextPCB mock/qualified fixtures | no TextPCB kernel types | qualify only after generic contracts land |
| 61.1 | `cross-capability-stress-corpus` | Permanent adversarial corpus | DESIGNED | proof of public claims under cross-capability attacks | existing specialized adversarial suites provide seed corpus | all | stale/forged/poisoned/UNKNOWN/unsupported/refinement/resource attacks | tests establish only covered properties | make permanent and cumulative |
| 62.1 | `hosted-foundation-review` | Semantic Solver contract + hosted-foundation review | DESIGNED | hosted fabric must consume public semantics without private bypass | architecture review milestone | all | claim-to-gate audit + boundary review | no hosted-semantic bypass claim until review passes | execute after governed semantic evolution is substantially real |

## Reconciliation-discovered physical/distributed seams

The Embedded/Physical architecture review exposed additional requirements that are not fully represented by rows 57–60. They are recorded here now so the known destination cannot be lost, but implementation sequencing is deferred to the dedicated integration plan.

| ID | Milestone | Capability | Status | Existing substrate | Missing semantic elevation |
|---|---|---|---|---|---|
| PHY-01 | `physical-authority-capabilities` | Authority domains, leases/epochs, bounded revocable effect capabilities, semantic preemption | DESIGNED | scoped grants/delegation/deny/expiry; typed capability ABI; effect authority evidence | exclusive authority-domain ownership, epoch freshness, capability non-amplification, explicit preemption/revocation semantics |
| PHY-02 | `authoritative-state-claims` | Desired / predicted / observed / authoritative state separation | DESIGNED | revisions, Evidence, effect intent/result, external-state design | generic typed state-claim contract + fact-authority resolution; command must not overwrite observation |
| PHY-03 | `postcondition-verification` | Command ≠ achievement; postcondition verifier and transition-attempt lifecycle | DESIGNED | EffectSpec pre/postconditions; ownership/reconciliation/UNKNOWN | generic observation-backed postcondition verification and authoritative commit rule |
| PHY-04 | `temporal-causal-semantics` | sequence, causal relation, leases/deadlines, observation age, clock quality | DESIGNED | event order, timestamps, lease expiration in existing subsystems | explicit causal/partial-order contract; monotonic device epochs; clock-quality/freshness semantics |
| PHY-05 | `physical-identity-trust` | device/component identity, calibration lifecycle, trust boundary, attestation | DESIGNED | external refs, environment fingerprints, measurement authority, runtime provenance | physical assembly/sensor/calibration identity; validity ranges/expiry; trust claims; secure-boot/firmware attestation hooks |
| PHY-06 | `degraded-autonomy-safety` | degraded modes, safety envelopes, semantic preemption, hybrid discrete/continuous guard semantics | DESIGNED | machine states/obligations, continuous IR, effects, scoped authority | degradation policy, continuous safety envelope, hybrid state contract, emergency/local authority rules |
| PHY-07 | `observation-epistemics` | observation lifecycle, fusion, source independence, epistemic containment | DESIGNED | Evidence, measurement authority, proof/evidence grades, no-voting solver doctrine | raw→calibrated→derived/fused lifecycle; fusion contract; no authority laundering invariant across transformations |
| PHY-08 | `epistemic-risk-obligations` | assumptions, epistemic debt, risk/hazards, irreversibility, pre/post obligations | DESIGNED | assumptions/reasoning artifacts, semantic dependencies, verification debt design, EffectSpec `reversible`/`compensation` | generalized epistemic-debt propagation, hazard/risk envelope, irreversible-action evidence escalation, obligation phase taxonomy |
| PHY-09 | `governed-experiments` | experiment contract and information-value evidence acquisition | DESIGNED | refinement design, resources, Evidence, verifier planning | hypothesis/control/measurement/procedure contract; experiment selection under safety/evidence/resource constraints |
| PHY-10 | `portable-kernel-machine-compiler` | language-neutral kernel semantics, stable machine IR, differential replay, Rust/std/no_std | DESIGNED | portable semantic archive, typed IRs, deterministic fingerprints, formal models | explicit kernel boundary independent of Python/DB/OS; canonical machine IR; Python/Rust conformance oracle; bounded no_std profile |
| PHY-11 | `embedded-realtime-qualification` | embedded-hal-style semantic executor traits, RTIC mapping, sim→SIL→HIL→physical qualification, safety profile | DESIGNED | provider/capability manifests, effects, resource governance, adapter conformance | embedded executor profile, timing contracts, interrupt/event bridge, qualification-level evidence binding, safety-development restrictions |

These rows are **not** a separate Embedded AASM product. They extend the same authority, Evidence, resource, effect, revision, knowledge, verification, and refinement planes already used by the public engine.

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

This immutable release completes **56.1 Solver Outcome v2**. It does not imply release of 56.2 or later work.

## Current development qualification evidence

On development head `99b379a2162758e384563bd42150dae3025ca87d`, the following exact-head contexts were observed passing after the version/release identity reconciliation:

- `aasm/scoped-authority`
- `aasm/v54`
- `aasm/v55`
- `aasm/proof-claims`
- `aasm/solver-learning`
- `aasm/solution-pools`
- `aasm/v56-provenance`
- `aasm/formal-assurance`
- `aasm/optimization`
- `aasm/semantic-solver-rc`
- `aasm/v56`

The generic `aasm/ci-summary` on that head still had a unit-test failure while wheel, LangGraph, adapter conformance, scopes, PostgreSQL, and Compose were green. CI has since been instrumented to annotate exact pytest failures; do not promote the current development target to an immutable release until the full selected release gate is green.

## Immediate builder queue

1. Keep `v0.56.0` / `551b2f47…` as the immutable published boundary.
2. Keep 56.2 in the existing 0.56.1 development target and finish current-head generic CI qualification; do **not** publish automatically.
3. Reconcile the dormant reproducibility/provenance-v2 implementation against the active 56.2 provenance contract before any 56.3 admission.
4. Finish the dedicated Governed Physical and Distributed Reality reconciliation against current source before implementing PHY rows.
5. Then produce the new integration plan as a dependency-ordered extension of the existing roadmap—no parallel truth/authority/resource/effect subsystem and no version-per-feature numbering.
6. Keep TextPCB as a demanding consumer/conformance target; do not move TextPCB-specific types into the kernel.

## Completion discipline

A row advances to `TESTED` only with reproducible tests. It advances to `GATED` only when the declared gate executes those claims on an exact Git head. It advances to `RELEASED` only when an immutable published package/tag exposes the capability without exceeding the evidence.

Development may continue from a sufficiently qualified prerequisite without forcing an intermediate package publication. Package SemVer is assigned at a deliberate coherent release boundary under `docs/VERSIONING.md`.
