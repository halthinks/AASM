# AASM Roadmap

AASM is currently **v0.40.0 / experimental**.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- **v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection — Current — implemented**

## v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

Delivered:

- canonical sensory/working/episodic/semantic/procedural memory objects;
- Decision → Obligation → Evidence memory mutations;
- exact authorized-object commit;
- semantic memory restricted to V37 admitted knowledge;
- V38 stale/refuted propagation into memory visibility;
- scope and principal privacy;
- deterministic retention and tombstone forgetting;
- derived retrieval indexes that never change canonical memory identity;
- bounded Reasoning Frontier;
- bounded deterministic Context Projection;
- replay/restart, schema, CLI, server rebinding, conformance, and formal assurance;
- legacy `DPMemory` preserved as the algorithmic memo cache.

## v0.41.0 — Domain-Neutral Autonomous Solver Loop

**Next.** Close the loop over the existing semantic, epistemic, capability, truth-maintenance, and memory layers.

```text
compile / ingest
   ↓
context + reasoning frontier
   ↓
select next obligation / information gap / objective
   ↓
propose candidate decision or capability action
   ↓
authority / policy
   ↓
lease typed capability
   ↓
execute / observe
   ↓
Evidence
   ↓
verify / admit
   ↓
truth maintenance
   ↓
re-project context
   ↓
continue | backjump | investigate | complete
```

Requirements: deterministic frontier selection, fairness/resource constraints, information-gap handling, v0.39 capability routing, ordinary Evidence ingestion, v0.37 admission, v0.38 truth maintenance, v0.40 context reprojection, deterministic completion/failure criteria, pause/resume, user steering, and exact replay. No new scheduler/event log/epistemic store.

## v0.42.0 — Reference Domains and Stress Tests

Exercise the full loop across constraint solving, software repair, research synthesis, mathematical/formal reasoning, and long-horizon memory consolidation.

## v0.43.0 — Semantic Conformance and Adversarial Certification

Certify domain packages, compilers, reasoning, truth maintenance, capabilities, formal verifiers, memory/context, solver traces, and recovery with `PASS | FAIL | INCONCLUSIVE` adversarial fixtures.

## v0.44.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, retention/privacy, revocation/supersession, and explicit receiving-run admission.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, packaging, and upgrade gates pass.
