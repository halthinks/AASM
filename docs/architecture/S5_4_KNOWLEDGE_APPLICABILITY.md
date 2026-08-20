# S5.4 Governed Knowledge Applicability and Application

**Status:** pre-admission semantic/durable-runtime foundation  
**Applicability contract:** `aasm.knowledge.applicability.v1`  
**Application contract:** `aasm.knowledge.application.v1`  
**Runtime:** `aasm.knowledge.applicability.runtime.v1`  
**Qualification:** `aasm/knowledge-applicability`

## Purpose

S5.4 makes reusable knowledge a governed input rather than an implicit source of truth or authority.

The stage boundary is explicit:

`selected != applicable != applied`

A retrieval/ranking decision can nominate knowledge. It cannot prove that the knowledge applies to the current target. An applicability assessment can prove or reject target-local transfer predicates. It cannot authorize use. Application requires an independent authorization from the existing AASM authority plane.

## KnowledgeItem

`KnowledgeItem` binds content to a knowledge kind, source scope/object identity, exact source semantic fingerprint, explicit applicability scopes and predicates, invalidation triggers, local source Evidence, optional source-run identity, optional freshness, and confidence metadata. Source authority transfer is always `NEVER`.

## KnowledgeSelection

`KnowledgeSelection` records why an exact `KnowledgeItem` was retrieved for an exact target scope and target semantic fingerprint. Its canonical identity states both `applicability_claim = NONE` and `authority_claim = NONE`. Performance knowledge can therefore influence search/routing without retrieval relevance becoming semantic validity.

## ApplicabilityCheck

Every predicate declared by the KnowledgeItem must be assessed exactly once as `PASS | FAIL | INCONCLUSIVE`. The overall result is derived: any `FAIL` is `INAPPLICABLE`; all `PASS` is `APPLICABLE`; otherwise the result is `INCONCLUSIVE`. `PASS` and `FAIL` require Evidence.

An applicability check cannot weaken the KnowledgeItem's invalidation triggers. Only one active assessment may exist for a selection. Reassessment uses the existing Evidence lifecycle by invalidating the prior applicability Evidence and appending the replacement. Applicability carries `authority_claim = NONE`.

## KnowledgeApplication and existing authority

Only a currently `APPLICABLE` check may reach the authority boundary. The runtime builds an ordinary existing AASM `Proposal` binding the exact KnowledgeItem, KnowledgeSelection, ApplicabilityCheck, target scope/fingerprint, application kind, and verification effect.

The existing `AuthorityPolicy.authorize()` produces the existing `AuthorizedAction`. S5.4 records a canonical AASM `AUTHORIZED` event containing the authorization ID, authority, exact proposal, and proposal fingerprint. A durable `KnowledgeApplication` is accepted only when replay can locate and verify that exact authorization event. Metadata cannot manufacture authority.

No `KnowledgeAuthority`, applicability authority, or parallel authority store is introduced.

## Freshness and semantic drift

Current use rechecks active item Evidence, selection Evidence, applicability Evidence, item/selection/applicability lifecycle state, target semantic fingerprint, and declared freshness. A target semantic fingerprint change therefore blocks application even when an old applicability assessment remains historically present.

## Verification firewall

`verification_effect` is explicit: `NONE | REDUCE | REPLACE`.

`REDUCE` or `REPLACE` can only appear inside the exact proposal authorized by the existing AASM authority plane. S5.4 itself performs **no verification-obligation mutation**. It records the governed authorization/application fact for a later qualified integration boundary. Reused knowledge therefore cannot silently reduce the current verification floor.

## Cross-run compatibility

S5.4 does not replace the v0.48 cross-run contracts. `knowledge_item_from_cross_run_envelope()` adapts a `CrossRunKnowledgeEnvelope` while preserving foreign Evidence/artifact/provenance as metadata and retaining `source_authority_transfer = NEVER`.

`applicability_check_from_cross_run_certificate()` converts the existing receiving-run admission certificate into an explicit applicability predicate. Even after it passes, the receiving run must separately authorize application using its own AASM authority plane. Foreign controller identity, authority, and resource entitlement never transfer.

## Durable runtime

S5.4 persists four append-only record types as canonical AASM Evidence:

- `KNOWLEDGE_ITEM`
- `KNOWLEDGE_SELECTION`
- `APPLICABILITY_CHECK`
- `KNOWLEDGE_APPLICATION`

The projection is reconstructed from AASM Evidence and Event replay. There is no parallel knowledge store, applicability store, or authority plane. The runtime performs no effect dispatch, resource reservation, problem mutation, or verification mutation.

## Admission boundary

S5.4 remains `PRE_ADMISSION_ONLY` and absent from the active public root until its semantic, runtime, cross-run compatibility, and adversarial authority corpus qualify.
