# AASM Roadmap

AASM is currently **v0.39.0 / experimental**.

A release is complete only when ordinary source is reachable from `main`, package/runtime/README agree, CI and formal assurance pass, the immutable tag points to the exact commit, and remote release assets verify.

## Completed foundation

| Release | Capability | State |
|---|---|---|
| v0.29.0 | Thin LangGraph Adapter | Released |
| v0.30.0 | Adapter Conformance Kit | Released |
| v0.31.0 | Hierarchical Decision Scopes | Released |
| v0.32.0 | Runtime/Formal Trace Conformance | Released |
| v0.33.0 | Signed Provenance and Verifiable Exports | Released |
| v0.34.0 | Distributed Recovery Certification | Released |
| v0.35.0 | Semantic Problem Model Foundations | Released |
| v0.36.0 | Semantic Compiler SDK | Released |
| v0.37.0 | Reasoning Artifacts and Epistemic Admission | Released |
| v0.38.0 | Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance | Released |
| **v0.39.0** | **Typed Protocol, Capability ABI, and Formal Verification Workers** | **Current — implemented** |

## How the expanded modules fit

The expanded designs remain sequenced by the invariant each needs:

| Original module / extension | Roadmap placement | Why |
|---|---|---|
| Rich Causal Decisions & Reactive Obligations | **v0.38** | Needs admitted reasoning plus dependency-local invalidation |
| Refined Typed Legal Transitions | **v0.39** | Becomes the typed event/transition protocol rather than a second state engine |
| ATP / SMT / proof-assistant integration | **v0.39** | Becomes the first reference `VERIFIER` capability family under the same ABI |
| Hierarchical Memory Layer | **v0.40** | Must retrieve only against validity/staleness already established by v0.37–v0.38 and capability evidence established by v0.39 |

## v0.39.0 — Typed Protocol, Capability ABI, and Formal Verification Workers

V0.39 turns legal transition vocabularies and executable tools into versioned, authority-aware contracts.

Delivered:

- deterministic `TypedEventSchema`, `ScopedLegalTransition`, and `PatternMachine`;
- typed payload validation before any durable transition proposal;
- policy/controller admission for pattern versions rather than direct `register_pattern()` authority;
- typed transition proposals represented by existing `CausalDecisionRecord`s;
- guards, evidence contracts, and declared transition work compiled into ordinary `ObligationRecord`s;
- transition activation only after obligations are `VERIFIED`/`COMMITTED` and policy/controller authorization is present;
- scope-aware typed state using existing hierarchical decision scopes;
- versioned `CapabilityContract` and `CapabilityProvider` identities for `OPERATOR`, `OBSERVER`, `VERIFIER`, and `HANDLER` capabilities;
- scheduler binding through existing `ResourceRecord` capability tokens and `TaskLease` ownership;
- no capability-owned scheduler, reducer, database, or effect authority;
- provenance-bearing `FormalStatement` records binding exact source reasoning-artifact fingerprints to canonical formal source;
- first formal verifier capabilities for Vampire/TPTP, Z3/SMT-LIB2, cvc5/SMT-LIB2, Lean 4/kernel checking, and certificate checking;
- explicit query modes: `VALIDITY`, `SATISFIABILITY`, `COUNTERMODEL`, `EQUIVALENCE`, `INVARIANT`;
- SMT validity semantics tied to `ASSUMPTIONS_AND_NEGATED_CONJECTURE`;
- Lean proof rejection explicitly `NOT_A_REFUTATION`;
- canonical formal result statuses and verification strengths;
- reproducible provider identity through solver version plus executable SHA-256 or immutable container digest;
- raw output and proof objects separately content-hashed from semantic theorem/request identity;
- independent solver agreement without majority-vote truth semantics;
- disagreement => `INCONCLUSIVE`;
- formal requests represented by ordinary AASM obligations and provider-specific `TaskDemand`s;
- formal result acceptance requires a live matching `TaskLease` and an admitted compatible provider;
- solver results become Evidence only; linked reasoning artifacts move through the v0.37 `VERIFY` transition and still require policy/controller authorization;
- standalone successful formal work proposes `Lemma`/`Invariant`; countermodels propose `Counterexample`; none auto-authorize;
- exact restart/replay preservation through existing Memory/SQLite/PostgreSQL state/event paths;
- CLI, JSON schemas, executable conformance, and bounded TLC/SPIN authority models.

The formal reasoning pipeline is intentionally:

```text
ReasoningArtifact
      ↓ exact fingerprinted formalization
FormalStatement
      ↓ ordinary obligation + provider-specific task
TaskLease
      ↓
Vampire / Z3 / cvc5 / Lean 4
      ↓
FormalVerificationResult Evidence
      ↓
v0.37 VERIFY
      ↓
POLICY / CONTROLLER authorization only
      ↓
v0.38 truth-maintenance consequences
```

## v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

**Next.** Build first-class, durable, scope-aware long-horizon memory on the validity and capability substrate now established by v0.37–v0.39.

Canonical memory will contain durable references/content, semantic fingerprints, scopes, causal lineage, epistemic state, retention/privacy policy, capability/evidence provenance, and source provenance. Embeddings and other retrieval structures are **derived indexes**, never memory identity or truth.

Planned memory kinds:

- sensory;
- working;
- episodic;
- semantic;
- procedural.

Semantic memory will reference admitted reasoning instead of becoming a second truth system. Formal proofs/certificates remain Evidence or reasoning provenance and can be ranked by verification strength.

Context projection will combine:

- hierarchical scope visibility;
- `VALID` / `STALE` / `REFUTED` / `AUTHORIZED` state;
- dependency depth;
- causal and objective relevance;
- verification strength and recency;
- capability/provider provenance when relevant;
- retention/privacy policy;
- bounded frontier/context budgets.

Forgetting must preserve append-only provenance semantics through tombstoning, visibility revocation, or cryptographic-erasure policy rather than silently deleting history.

## v0.41.0 — Domain-Neutral Autonomous Solver Loop

Close the loop:

`Compile → memory/frontier projection → candidate → epistemic admission → causal decision → obligation → typed capability execution/observation → verify → truth maintenance → learn → backjump/restart`.

Reactive obligations become executable only through the v0.39 typed capability path. Formal verifier selection likewise becomes an automatic capability-routing decision here, without transferring epistemic authority to the solver.

## v0.42.0 — Reference Domains and Memory/Reasoning Stress Tests

Reference domains will exercise the full stack across:

- finite constraints;
- software delivery and repair;
- research evidence synthesis;
- **mathematical/formal theorem proving** with Vampire, Z3, cvc5, Lean 4, proof/countermodel provenance, disagreement fixtures, and long-horizon theorem dependency graphs.

## v0.43.0 — Semantic Conformance and Adversarial Certification

`PASS | FAIL | INCONCLUSIVE` across packages, compilers, reasoning admission, dependency traces, typed protocols, capability providers, formalization fidelity checks, solver evidence, memory projections, truth-maintenance traces, and authority boundaries.

Adversarial fixtures should include malformed typed payloads, capability impersonation, stale/superseded leases, provider-version mismatch, solver disagreement, forged proof/result fingerprints, mistranslated formalizations, and attempted solver self-authorization.

## v0.44.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in, provenance-bearing, applicability-scoped, revocable, version-aware reusable knowledge and cross-run memory. Formally verified results are prime candidates, but reuse must preserve exact theorem/formalization/environment/proof/provider identities and invalidate when applicability assumptions change.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the first coherent solver contracts after replay, formal, distributed, adversarial, memory, reference-domain, typed-capability, proof-verification, and packaging gates pass.
