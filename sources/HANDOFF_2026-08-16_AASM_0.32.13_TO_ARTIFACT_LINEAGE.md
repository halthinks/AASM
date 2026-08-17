# AASM Handoff — 0.32.13 Qualified Boundary → Artifact Lineage

**Date:** 2026-08-16  
**Repository:** `halthinks/AASM`  
**Package SemVer:** `0.56.1`  
**Public adoption level:** `0.32.13`  
**Current qualified documentation head:** `5d0a2ae9c31c78e75f2145c8460cfd87baef4bc0`  
**Prior fully qualified implementation/release-wired head:** `55a8da1f6937d97439a6e2103a55d1b6f6d0f4fd`  
**Status:** 25/25 custom qualification contexts green on the documentation-sync head.

---

## 1. Purpose of this handoff

This document is the canonical continuation point after repeated session interruptions. It records the exact state of AASM at public adoption `0.32.13`, the work that has already landed and been qualified, the architectural constraints that must not be regressed, and the next implementation slice.

The next builder must **not reconstruct the program from memory** and must **not reopen already-qualified design decisions** unless new evidence demonstrates a defect. Continue from this boundary.

---

## 2. Current architectural direction

AASM remains a governed reasoning and supervisory-control kernel over:

- external authoritative state machines;
- typed engineering artifacts;
- heterogeneous solvers;
- physical and epistemic evidence;
- verification/refinement loops;
- durable provenance and replay;
- controlled accumulation of engineering knowledge.

The expansion into physical evidence, observation epistemics, artifact lineage, refinement, and engineering knowledge is **additive**. It does not replace AASM's prior state-machine, authority, planning, conflict, assurance, replay, resource-governance, or agent-supervision functions.

AASM must continue to separate:

1. **what was observed**;
2. **what was processed or inferred**;
3. **what is currently trusted or admitted**;
4. **what external authority actually controls**;
5. **what action is proposed**;
6. **what action is authorized**;
7. **what action was executed**;
8. **what the resulting artifact/entity revision actually is**.

No later layer may collapse these distinctions.

---

## 3. Qualified S3 physical-evidence chain

The S3 chain is now qualified through observation lifecycle and fusion.

### 3.1 Already admitted and gated

The cumulative qualified chain is:

`causality → freshness → identity/calibration/trust → execution environment → observation lifecycle/fusion`

The observation lifecycle/fusion slice introduced:

- lifecycle semantic contract;
- lifecycle runtime;
- fusion semantic contract/runtime;
- shared Evidence-backed projection;
- lifecycle/fusion schemas;
- adversarial and replay tests;
- source-contract firewall;
- dedicated `aasm/observation-epistemics` gate;
- active-engine admission;
- public API admission at `0.32.13`;
- cumulative S3 and v56 qualification;
- manual-release contract wiring.

### 3.2 Core lifecycle rules already locked

The implemented semantic boundary requires:

- raw lifecycle roots reference existing machine observations;
- later lifecycle stages preserve exact source ID and fingerprint lineage;
- dispositions are append-only;
- stage progression is semantic, not cosmetic;
- callers cannot merely relabel a raw reading `CALIBRATED`, `DERIVED`, or `VALIDATED`;
- `CALIBRATED` requires exact predecessor evidence plus active calibration and explicit time/environment context;
- stale, disputed, or rejected sources cannot silently re-enter later processing;
- lineage cycles are rejected;
- replay reconstructs the same lifecycle/fusion projection.

`VALIDATED` is **not** universal admission and does not create state authority.

### 3.3 Core fusion rules already locked

Fusion:

- cannot directly fuse raw machine observations;
- requires at least two exact lifecycle/fusion source fingerprints;
- records exact source lineage;
- rejects forged source fingerprints;
- cannot turn consensus into authority;
- may carry Evidence-backed independence declarations, but those declarations are non-authoritative;
- cannot create FactAuthority or source trust merely because multiple inputs agree.

### 3.4 Source firewall already locked

The observation-processing runtime must not:

- create state claims;
- create `FactAuthority`;
- create source trust;
- authorize or dispatch effects;
- use hidden host wall-clock time;
- create a parallel observation/truth store.

Lifecycle, fusion, and dispositions share the existing Evidence projection rather than introducing independent stores.

---

## 4. Important implementation commits

The interruption sequence landed the observation-epistemics slice incrementally. Important commits include:

- `6768fab1fe0b6400dadd1edc90ab4c1c17886be0` — fusion semantic contract;
- `f92c98609b9d7180049104877d34507829cfa9c4` — shared lifecycle/fusion runtime;
- `489c8d33dfdeb96f741bc0a5ef3872bcef60b042` — wire schemas;
- `cbf06f34b7c1a5dcce06bc0719755cbacf966f7a` — adversarial/replay corpus;
- `9782284235ffd18f7938e27cccc141238a81e6e8` — source-contract firewall;
- `f3427557ab7e7e8b4394fd7e5ba5de100461b3ba` — dedicated pre-admission gate;
- `64cff6e28147e54b31589b762e9595075969ebd1` — runtime admitted to active engine;
- `3ecfd421dbbed7688e9d9844d57e1d0b0c36773a` — adversarial corpus switched to actual active engine;
- `6bd4459eb1d080db8a6fcae9cf2a198ba7e510c2` — public surface advanced to `0.32.13`;
- `419abdac1dc7be064820b0cdaf8edb6a8c76b818` — public-candidate surface synchronized;
- `41c0df8c90fb52e91d4e8656051a2414cf723e33` — cumulative physical-evidence gate includes lifecycle/fusion;
- `bc1149ee5671ba6463556ba30fb4cc397eb8cacc` — cumulative v56 boundary updated;
- `eda6b1cb0aacda0c6d45513066384f3e699b6d9e` — release-source validation updated;
- `55a8da1f6937d97439a6e2103a55d1b6f6d0f4fd` — release graph complete and 25/25 custom contexts green;
- `ef489afa747a27e71e6af7166c3e9e84a5b4b00f` — top roadmap synchronized;
- `66f8f86a1a278263cda48cb4a1295147db2742cd` — execution ledger synchronized;
- `5d0a2ae9c31c78e75f2145c8460cfd87baef4bc0` — deep unified engineering/Rust roadmap synchronized; this documentation head also reached 25/25 green.

---

## 5. Qualification state

At the qualified boundary, all 25 custom contexts were green, including the important cumulative and public gates:

- `aasm/observation-epistemics`;
- `aasm/execution-environment`;
- `aasm/physical-evidence`;
- `aasm/v56`;
- `aasm/ci-summary`;
- formal assurance;
- semantic RC;
- inherited PR-1/PR-2/PR-3 qualification gates.

The cumulative S3 gate proves the physical-evidence chain together rather than merely proving isolated child features.

The cumulative v56 gate proves public-candidate tests, inherited qualification gates, S3 qualification, release source contract, and the live `0.32.13` claim ceiling.

No release/tag was triggered as part of this work. Manual release remains manual-only.

---

## 6. Canonical roadmap status

The three canonical planning surfaces were synchronized after qualification:

1. top-level roadmap;
2. canonical execution ledger;
3. deep unified engineering/Rust roadmap.

They now reflect:

- public adoption `0.32.13`;
- execution-environment: **GATED**;
- observation lifecycle/fusion: **GATED**;
- next builder target: **artifact revision lineage + entity evolution**.

The future S4–S11 program remains intact. Do not truncate or collapse it while advancing the next slice.

---

## 7. Exact next implementation target

### NEXT: artifact revision lineage + entity evolution

The next slice should introduce first-class contracts tentatively named:

- `aasm.artifact.revision.v1`;
- `aasm.entity.evolution.v1`.

The intended dedicated qualification context is:

- `aasm/artifact-lineage`.

This must be developed **pre-admission first**, following the same pattern used successfully for observation epistemics:

1. inspect existing artifact/reference/back-end substrate;
2. define semantic contracts;
3. implement runtime against existing durable Evidence/revision infrastructure;
4. pin schemas;
5. build adversarial + replay corpus;
6. add source firewall;
7. create dedicated pre-admission `aasm/artifact-lineage` gate;
8. obtain green pre-admission evidence;
9. compose runtime into the active engine;
10. rerun corpus against the real imported engine;
11. expose only proven methods/contracts publicly;
12. advance public adoption only after qualification;
13. wire cumulative S3/S4/v56/release-source/manual-release gates as required;
14. re-qualify exact final head;
15. update roadmap/ledger only after the exact code head is green.

---

## 8. Critical design constraint for artifact lineage

**Do not create another artifact registry.**

The interrupted work had just begun inspecting the existing artifact/storage substrate for this reason. Artifact revision lineage must reuse AASM's current durable artifact/reference/Evidence/revision machinery wherever possible.

The new layer must not create a second source of truth for:

- “current artifact”;
- artifact identity;
- revision history;
- entity identity;
- entity current state;
- authoritative external state.

If a projection is useful for queryability, it must be a replayable projection derived from durable canonical records, not an independent truth plane.

---

## 9. Proposed semantic model for `aasm.artifact.revision.v1`

The next implementation should formalize, at minimum:

- stable artifact identity separate from revision identity;
- immutable revision identifiers/fingerprints;
- predecessor revision reference(s);
- exact content/provenance fingerprinting;
- producer/process/tool identity where available;
- source Evidence references;
- environment reference where material;
- optional refinement-loop/run reference;
- explicit revision relation (`CREATED_FROM`, `MODIFIES`, `DERIVED_FROM`, `MERGES`, etc.) rather than inferred replacement;
- append-only revision history;
- no silent mutation of an already-recorded revision;
- no automatic authority merely because a revision is newer;
- deterministic replay of lineage.

A “latest” revision may be a query projection, but **newest is not automatically authoritative, validated, accepted, or active**.

---

## 10. Proposed semantic model for `aasm.entity.evolution.v1`

Entity evolution should solve the related but distinct problem of a persistent real or logical entity changing across artifact revisions.

The contract should distinguish:

- entity identity;
- artifact/revision representations of that entity;
- observed physical state;
- declared intended state;
- authoritative external state;
- derived model state;
- lifecycle/evolution events.

Examples include:

- a PCB design entity across schematic/layout/fabrication revisions;
- a mechanical assembly across CAD/mesh/manufacturing revisions;
- a solver model across refinement iterations;
- a deployed physical system across inspection/maintenance/modification events;
- a software/agent configuration across governed revisions.

Entity evolution must not allow an artifact revision to silently overwrite physical truth or authoritative state.

---

## 11. Required adversarial cases for the next gate

The `aasm/artifact-lineage` corpus should include at least:

- forged predecessor revision ID;
- predecessor fingerprint mismatch;
- mutation of an immutable prior revision;
- revision cycle;
- self-parent revision;
- missing referenced source Evidence;
- stale/disputed/rejected Evidence misuse where policy requires active evidence;
- attempt to mark “newest” as authoritative solely by recency;
- attempt to overwrite entity identity through a new artifact revision;
- two competing child revisions from the same parent;
- explicit merge with incomplete parent set;
- duplicate content with different claimed provenance;
- entity evolution event referencing an unrelated artifact lineage;
- artifact revision attempting to create FactAuthority;
- artifact revision attempting to authorize/dispatch effects;
- hidden wall-clock dependence;
- parallel artifact/current-state store creation;
- SQLite restart/replay reconstructing identical lineage/evolution projection.

The corpus should also prove that branching is legal when explicit and that competing revisions remain distinguishable rather than being collapsed.

---

## 12. Required source firewall for artifact lineage

The new runtime should be rejected if it starts doing any of the following:

- creating FactAuthority or source trust;
- making effect authorization decisions;
- dispatching effects;
- mutating existing immutable revision records;
- using host wall-clock time as hidden semantic input;
- creating an independent “current artifact” truth store;
- creating an independent “current entity state” truth store;
- treating newest revision as accepted/validated/authoritative without explicit evidence/authority;
- bypassing existing Evidence/revision persistence abstractions.

---

## 13. Refinement-loop relationship

Artifact lineage is foundational for the broader first-class `RefinementLoop` architecture already identified for AASM.

The intended generic pattern is:

`solve → produce artifact revision → evaluate/measure/observe → record evidence → learn/refine → produce successor revision → verify`

This must not be special-cased for SPICE, EM, CFD, FEA, CAD, PCB, or any single solver. Those become adapters/participants in a generic governed refinement architecture.

Artifact lineage provides the immutable chain that allows AASM to know **what changed between iterations**, **which evidence justified the change**, **which solver/environment produced it**, and **whether a later revision actually improved the governed objective**.

---

## 14. Engineering-knowledge accumulation relationship

This lineage is also prerequisite infrastructure for AASM as a controlled accumulation engine for engineering knowledge.

AASM should eventually be able to preserve, with provenance:

- successful and unsuccessful revisions;
- constraints discovered during solving;
- solver disagreements;
- validation outcomes;
- environment-sensitive behaviors;
- calibration dependencies;
- failure mechanisms;
- reusable derived knowledge;
- conditions under which prior knowledge is valid or invalid.

The system must accumulate knowledge without turning historical observations, model outputs, or consensus into unearned authority.

---

## 15. Resource-governance requirement remains active

Known desired resource governance must be engineered from the product backwards, not deferred to an “eventually” bucket.

AASM's resource model should be capable of representing governed scarce resources including, where available:

- provider quota;
- model/API tokens;
- weekly subscription usage budgets;
- monetary spend;
- wall time;
- compute capacity;
- scarce expert-model usage;
- solver licenses/slots;
- human review capacity.

Optimization should support the previously established direction:

**maximize** correctness, evidence quality, and expected progress;  
**minimize** provider quota burn, monetary cost, wall time, and scarce expert-model usage.

Artifact/refinement work must leave clean seams for this resource accounting rather than assuming compute is free or unlimited.

---

## 16. Public/private architecture constraint remains active

The hosted fabric may remain private, but public AASM must retain stable seams now so future hosted capability does not require tearing up machines, stores, authority, export, tenancy, or resource accounting.

Public code should continue to assume durable records can be scoped by principal/workspace/tenant where applicable and should avoid global-singleton semantics that would make later isolation impossible.

---

## 17. Working method to continue

The prior successful implementation discipline should be preserved:

- work directly from live GitHub `main` as source of truth;
- inspect exact current files before writes;
- additive changes only unless a replacement is required by the contract;
- no stale synthetic test engine after active admission;
- pre-admission gate before public surface exposure;
- exact-head qualification after each meaningful admission boundary;
- cumulative gates must include the new child gate;
- release-source checker must know every required contract/schema/checker/workflow/test/public block;
- manual release context list must include the new gate before release eligibility;
- no release/tag merely because implementation work lands;
- update roadmap/ledger after qualification, not before;
- preserve previous provenance and qualification heads rather than rewriting history.

If a small CI/test interruption appears, diagnose and repair it rather than merely reporting it.

---

## 18. Immediate resume instruction

**Resume here:** inspect the current repository for existing artifact/reference/back-end persistence and revision semantics. Reuse them. Then draft `aasm.artifact.revision.v1` and `aasm.entity.evolution.v1` semantic contracts and implement a pre-admission runtime/projection with no independent artifact truth store.

Do **not** begin by changing the active public engine. The next first visible qualification milestone should be a green dedicated pre-admission `aasm/artifact-lineage` gate.

---

## 19. Non-regression summary

Do not regress these already-qualified boundaries:

- durable/replayable state-machine semantics;
- authority separation;
- evidence provenance;
- causality;
- freshness;
- identity/calibration/trust;
- execution environment;
- observation lifecycle;
- fusion without consensus authority;
- no hidden wall-clock semantic dependence;
- no parallel truth stores;
- effect authorization/dispatch separation;
- release-source contract discipline;
- cumulative qualification gates;
- public adoption ceilings.

The new artifact/entity capability is **another capability of AASM, not its sole function or end state**.
