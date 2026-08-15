# AASM Governed Semantic Evolution — Execution Ledger

**Status projection date:** 2026-08-15  
**Baseline:** released v0.55.0 at tag `v0.55.0` / commit `dd9360858be8755a5639162a7d388d867c1b01e6`  
**Doctrine:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`  
**Roadmap:** `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`  
**Source lock:** `docs/source_material/SOURCE_LOCK_MANIFEST.md`

This is the canonical mutable progress ledger. It may advance or refine work items, but locked requirements may not disappear. When an item is split, the parent row remains and points to its children.

Dormant or interrupted source code for a future release does **not** advance a ledger row by itself. A future row advances only when that release is resumed in sequence and its contract/runtime/test/gate evidence is deliberately qualified. This rule applies to the interrupted v0.56 files that existed before v0.55 was actually released.

## Status vocabulary

`SOURCE_LOCKED | DESIGNED | CONTRACT_LANDED | RUNTIME_LANDED | TESTED | GATED | RELEASED | BLOCKED`

## Active execution ledger

| ID | Release | Capability | Status | Primary source requirement | Current code/contracts | Dependencies | Acceptance / adversarial evidence | Claim ceiling | Gate / next action |
|---|---:|---|---|---|---|---|---|---|---|
| SRC-001 | cross | Source lock and doctrine | SOURCE_LOCKED | Preserve supplied TextPCB/AASM sources; prevent implementation drift | Whitepaper, canonical roadmap, source-lock manifest; exact source bundle retained separately | v0.55 baseline | immutable hashes + baseline commit + precedence/no-overwrite rules | architecture doctrine only | add new source revisions; never silently rewrite locked sources |
| 55.1-A | 0.55 | ExternalReference | RELEASED | stable external requirement/decision identity through generated solver objects | `src/aasm/semantic_evolution.py`; `aasm.external.reference.v1`; schema; public v0.55 | semantic fingerprinting | exact-head v0.55 + full CI; deterministic round-trip + missing-identity rejection | stable v0.55 identity contract; no truth authority by identity alone | released in `v0.55.0` |
| 55.1-B | 0.55 | ProblemRevision | RELEASED | revision-bound evidence/solver/verifier/external-machine semantics | `aasm.problem.revision.v1`; Evidence projection + v0.55 runtime | ExternalReference | SQLite replay/restart; single durable head reconstruction; stale revision rejection | linear single-parent v0.55 transition foundation; no merge claim | released in `v0.55.0` |
| 55.1-C | 0.55 | ProblemDelta | RELEASED | deterministic change impact and refinement materialization | `aasm.problem.delta.v1`; typed semantic truth-change roots; schema | ProblemRevision; semantic dependencies | evidence-overlap rejection; exact stale-base fencing; target semantic fingerprint checks | deterministic declared delta; no universal domain-change inference | released in `v0.55.0` |
| 55.1-D | 0.55 | Revision transition + durable runtime | RELEASED | stale-result rejection; exact base/target binding; crash-safe change application | `validate_revision_transition`; `aasm.semantic-evolution.runtime.v1`; `runtime_v55_foundation.py` | ProblemRevision/Delta; v0.38 truth maintenance; v0.54 runtime | SQLite restart with pending impact; idempotent resume; replay equality; two-host stale writer rejection | existing Evidence/reducer authority only; no parallel truth table | released in `v0.55.0`; exact-head `aasm/v55` required |
| 55.2-A | 0.55 | Model feature set | RELEASED | fail-closed provider/model admission | `src/aasm/model_features.py`; `aasm.model.feature-set.v1`; schema | 55.1 revision binding | duplicate/revision-pair validation; exact vs approximate requirement fixtures | feature declaration/admission only | released in `v0.55.0` |
| 55.2-B | 0.55 | Provider capability manifest | RELEASED | provider feature/status/proof/provenance negotiation | `aasm.provider.capability-manifest.v1`; schema | 55.2-A | transformation/tolerance-policy requirements; missing feature fail-closed | capability evidence only; no provider truth authority | released in `v0.55.0` |
| 55.2-C | 0.55 | Model admission report | RELEASED | prevent unsupported/approximate semantics from silently entering provider execution | `aasm.model.admission.v1`; schema; `evaluate_model_admission` | 55.2-A/B | exact native/translated pass; exact-required approximation fails; verifier-only explicit | pre-provider semantic admission decision only | released in `v0.55.0` |
| 55.3 | 0.55 | Generalized formulation artifact | RELEASED | preserve variable/constraint/objective/external-reference mappings | `aasm.solver.formulation.v1`; certificate; execution binding; durable formulation runtime | 55.1, 55.2 | mapping completeness; reference resolution; revision fencing; identity checker; v0.54 bridge | built-in checker certifies exact identity only; nontrivial translation requires independent checker | released in `v0.55.0`; children 55.3-A–C extend model families |
| 55.3-A | 0.55 | Exact pseudo-Boolean/cardinality IR | RELEASED | richer exact discrete engineering constraints with formulation lineage | `src/aasm/discrete_ir.py`; typed PB/cardinality contracts; exact linearization certificate/schemas | 55.2, 55.3 | sampled semantic equivalence; tamper/wrong-transform rejection; constant contradiction handling | exact lowering only; approximation not supported by this contract | released in `v0.55.0` |
| 55.3-B | 0.55 | Portable scheduling IR | RELEASED | precedence/no-overlap/cumulative scheduling semantics without provider lock-in | `src/aasm/scheduling_ir.py`; scheduling model/assignment/validation/provider-binding schemas | 55.2, 55.3 | precedence/no-overlap/cumulative validation; fractional resource demand rejected; provider admission | portable semantics + independent assignment validation; complete scheduling execution adapter not claimed | released in `v0.55.0` |
| 55.3-C | 0.55 | Deterministic quadratic/conic IR | RELEASED | continuous engineering representation with explicit numerical policy | `src/aasm/continuous_ir.py`; canonical decimals; quadratic/SOC; tolerance/provider-binding schemas | 55.2, 55.3 | deterministic serialization; quadratic + SOC feasibility checks; tolerance binding | structural representation and assignment validation only; convexity/global optimality proof not claimed | released in `v0.55.0` |
| 55.4 | 0.55 | Shared objective-vector IR | RELEASED | semantic objectives ↔ optimization objectives; true lexicographic priorities | `src/aasm/decision_vector_ir.py`; hard floors + explicit objective priority; exact-linear compiler to v0.52 finite engine | 55.1, 55.2, 55.3 | hard-floor exclusion before objectives; priority-order fixtures; unsupported named/nonlinear compilation fails closed | `scalarization = NONE`; only exactly representable linear objectives compile | released in `v0.55.0` |
| 55.5 | 0.55 | Portable semantic-evolution archive | RELEASED | portable replay/export without hosted-only state | `aasm.semantic-evolution.archive.v1`; event history + canonical snapshot + derived projections + root hash | 55.1-55.4 | byte-stable round trip; section/root tamper rejection; existing-reducer replay equality; root-derived archive ID | archived events are replay input; snapshot is comparison evidence; sequence is ordering, not machine version | released in `v0.55.0` |
| 56.1 | 0.56 | Solver outcome v2 | GATED | normalized fine-grained solver outcomes with truthful provider termination/incumbent/bound/proof distinctions | `src/aasm/solver_outcome_v2.py`; `src/aasm/provider_status_v2.py`; `src/aasm/_runtime_v56_solver_outcome.py`; `schemas/solver-outcome-v2.schema.json`; `schemas/provider-status-map.schema.json`; additive `public_v56` candidate | released 55.2/55.3 | 33 focused contract/runtime/adversarial fixtures; independently validated incumbents; explicit lossy v2→v1 projection; exact native CaDiCaL/PySAT, OR-Tools CP-SAT, and HiGHS status qualification; full repository CI | `0.56.0.dev0` qualification candidate only; root package remains released v0.55.0; provider optimal status is not proof certification | exact-head `aasm/v56-status-v2` PASS at `86cf9199…`; **PAUSE before 56.2** |
| 56.2 | 0.56 | Execution profile + runtime provenance | SOURCE_LOCKED | evidence-grade deterministic execution | future release requirement; interrupted provenance files are dormant and excluded from v0.55 qualification | 55.3, 56.1 | effective-option/env/provider/adapter identity fixtures required | no v0.56 reproducibility claim yet | **PAUSED; resume only after explicit continuation from gated 56.1** |
| 56.3 | 0.56 | Reproducibility certification | SOURCE_LOCKED | truthful reproducibility claim levels | future release requirement; dormant interrupted tests do not count as qualification | 56.2 | semantic/assignment/objective/proof equivalence reruns required | none released | follow provenance after deliberate 56.2 implementation |
| 56.4 | 0.56 | Generic knowledge applicability/application | SOURCE_LOCKED | durable applicability-scoped learned constraints beyond solver learning | generalize v0.48/v0.53 mechanisms | 55.1, 56.1 | poisoned/cross-revision/cross-scope reuse attacks | solver-learning subset already real | design without second knowledge store |
| 56.5 | 0.56 | Integrated core/conflict pipeline | SOURCE_LOCKED | raw → normalized → minimized → independently rechecked external requirement core | reuse `conflict_minimization.py` | 55.1, 55.3, 56.1 | irrelevant-assumption/core oracle fixtures | generic minimizer exists; real pipeline incomplete | integrate after truthful outcome/formulation lineage |
| 57.1 | 0.57 | External machine binding | SOURCE_LOCKED | AASM supervises TextPCB state machine without mirroring truth | planned `aasm.machine.binding.v1` | 55.1, v0.54 effects | stale observed revision, out-of-band change | none yet | build over EffectIntent |
| 57.2 | 0.57 | Revision-safe machine transition | SOURCE_LOCKED | transition intent/receipt/expected state | planned `aasm.machine.transition.v1` -> v0.54 EffectIntent | 57.1, v0.54 ownership | no call before ownership; stale prestate rejects; UNKNOWN blocks retry | effect ownership already real | no second effect lifecycle |
| 57.3 | 0.57 | Artifact revision lineage | SOURCE_LOCKED | CAD/PCB/CAE artifacts are immutable revisioned outputs | planned | 55.1, 57.1 | tamper/parent lineage/stale artifact tests | existing artifact backend only | add canonical lineage |
| 57.4 | 0.57 | Entity evolution | SOURCE_LOCKED | persistent semantic identity across CAD topology/tool representation change | planned | 57.3 | ambiguous mapping blocks hard reuse | none yet | genericize beyond CAD |
| 58.1 | 0.58 | Governed refinement proposal/loop | SOURCE_LOCKED | solve→verify→learn→re-solve without direct verifier mutation | planned | 55.1, 56.4, 57.x | stale/self-authorized/no-progress refinement attacks | none yet | compose existing Evidence/reasoning/authority |
| 58.2 | 0.58 | Verification planning/debt | SOURCE_LOCKED | multi-fidelity evidence acquisition and release debt | planned | resources, verifier ABI, 55.1 | cheap-pass must not clear stronger obligation | none yet | projection over existing obligations/evidence/resources |
| 59.1 | 0.59 | Quantity/unit/tolerance semantics | SOURCE_LOCKED | engineering dimensional correctness | planned | 55.1 | dimensional mismatch/rounding/tolerance fixtures | none yet | generic quantity contract |
| 59.2 | 0.59 | Rule applicability/precedence | SOURCE_LOCKED | hard floor / hard / policy / preference / advisory semantics | planned | 55.1, 59.1 | override/waiver/priority attacks | none yet | keep distinct from objective priority |
| 59.3 | 0.59 | Semantic projection/equivalence | SOURCE_LOCKED | meaningful top-K/diversity/cross-backend equivalence | planned | 55.1, 55.3 | auxiliary-variable differences collapse under semantic projection | none yet | use across pools/reuse/artifacts |
| 59.4 | 0.59 | Production lexicographic/Pareto | SOURCE_LOCKED | scalable objective ordering/frontier truth levels | extend v0.52 exact finite reference | 55.4, 56.1, 59.3 | exact finite oracle qualifies production paths | exact finite already released | preserve claim levels |
| 59.5 | 0.59 | Scalable pools/top-K/diversity | SOURCE_LOCKED | real generated alternatives | extend v0.51 pools | 59.3, 59.4 | top-K/near-optimal/diverse/restart fixtures | complete finite currently released | truthful partiality |
| 59.6 | 0.59 | Proof/checker expansion | SOURCE_LOCKED | SAT proof transport; LP/MILP claims where genuine | extend v0.50 proof plane | 55.3, 56.1/56.2 | forged/mismatched proof artifacts | bounded proof plane already released | provider-specific claim ceilings |
| 60.1 | 0.60 | Uncertainty/scenario/temporal | SOURCE_LOCKED | operating modes, manufacturing variation, transient requirements | planned | 55.1, 59.1 | nominal-vs-robust claim separation | none yet | generic contracts |
| 60.2 | 0.60 | Readiness gate | SOURCE_LOCKED | deterministic completion/release predicate | planned | 57-60 | unresolved UNKNOWN/stale/debt/conflict blocks readiness | none yet | explanation-required |
| 60.3 | 0.60 | Engineering conformance + TextPCB qualification | SOURCE_LOCKED | generic external-domain kit; TextPCB as consumer | extend adapter conformance | all prior | realistic TextPCB mock/qualified fixtures | none yet | no TextPCB kernel types |
| 61.1 | 0.61 | Permanent stress corpus | SOURCE_LOCKED | adversarial proof of public claims | planned | all | cross-capability attack corpus | none yet | moved from old v0.56 milestone |
| 62.1 | 0.62 | Semantic Solver RC2 + hosted-foundation review | SOURCE_LOCKED | public engine can support hosted fabric without private semantic bypass | planned | all | claim-to-gate audit + architecture boundary review | none yet | moved from old v0.57 review |

## Verified exact-head v0.55 release evidence

Release commit: `dd9360858be8755a5639162a7d388d867c1b01e6`  
Tag: `v0.55.0`  
GitHub release workflow: `31912974049` — **SUCCESS**

Exact-SHA required statuses all passed on the release commit:

- `aasm/ci-summary`
- `aasm/formal-assurance`
- `aasm/semantic-solver-rc`
- `aasm/proof-claims`
- `aasm/solution-pools`
- `aasm/optimization`
- `aasm/scoped-authority`
- `aasm/solver-learning`
- `aasm/v54` parent compatibility
- `aasm/v55` active release qualification
- `aasm/release`

Release publication additionally passed:

- two byte-identical wheel/sdist builds;
- historical release audit + immutable release manifests;
- clean wheel installation and public-contract exercise;
- immutable tag target verification;
- remote GitHub release asset byte verification;
- SHA-256 manifest publication.

Earlier foundation evidence remains useful history:

- CI run `31906265347` at `45ef002a600d0e208c1c5ffb476415de48a820c5` covered initial 55.1 contract and 55.2 admission foundations.
- CI run `31906790298` at `053e10824f0ea9f685f529974c368af938b1d35b` covered durable 55.1 runtime, SQLite restart/resume, truth-maintenance integration, and stale two-host commit fencing.

## Verified exact-head v0.56 / 56.1 qualification evidence

Qualification implementation head: `86cf91990f729763f97687957657ce35bc186393`  
Dedicated status-v2 workflow: `31914353260` — **SUCCESS**  
Full repository CI workflow: `31914353204` — **SUCCESS**

Exact-head evidence includes:

- `aasm/v56-status-v2` PASS;
- `aasm/ci-summary` PASS;
- all focused Solver Outcome v2 contract/runtime/adversarial fixtures PASS;
- real CaDiCaL/PySAT, OR-Tools CP-SAT, and HiGHS native status identity/mapping qualification PASS;
- Python 3.11 / 3.12 / 3.13 full test suites PASS;
- reproducible wheel/sdist smoke PASS;
- PostgreSQL integration, Compose, hierarchical scopes, adapter conformance, and LangGraph integration PASS;
- all inherited v0.55/v0.54/formal/solver/proof/scoped-authority gates on the same head remained green.

This evidence qualifies **56.1 only**. It does not advance 56.2 or 56.3 and does not constitute a v0.56 package release.

## Immediate builder queue

1. **PAUSED HERE by explicit execution boundary.** 56.1 is GATED; do not advance 56.2 automatically.
2. On explicit resume, begin **56.2 Execution profile + runtime provenance** from the gated 56.1 contracts and released v0.55 parent boundary.
3. Keep 56.3 reproducibility certification SOURCE_LOCKED until 56.2 is implemented and gated.
4. Only after 56.1–56.3 are deliberately gated should 56.4 generic knowledge applicability and 56.5 integrated core/conflict pipeline advance.
5. Keep TextPCB as a demanding consumer/conformance target; do not move TextPCB-specific types into the kernel.

## Completion discipline

A row advances to `TESTED` only with reproducible tests. It advances to `GATED` only when the declared release gate executes those claims on exact head. It advances to `RELEASED` only when the active package/public surface and release documentation expose the capability without exceeding the evidence.

Dormant source, interrupted work, local experiments, or unqualified future-version files never count as `RELEASED` and do not permit skipping the declared sequence.
