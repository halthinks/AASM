# Formal Assurance

AASM adds an assurance layer over the conflict-learning calculus. The purpose is not to make every domain claim mathematically true. The purpose is to make the process by which machine knowledge becomes authoritative explicit, durable, independently checkable, and replayable.

## Certificate-gated hard knowledge

Under the default strict policy, an active hard learned constraint is legal only when a currently accepted durable verification covers its exact projection.

The enforced lifecycle is:

```text
conflict
  -> validated explanation
  -> SOFT learned constraint
  -> projection certificate
  -> independent verification
  -> explicit HARD promotion
```

This rule is enforced at the calculus commit boundary, not only in the promotion helper. Inherited methods, candidate activation, replayed state, deserialization, and later mutations cannot bypass it.

The policy can restrict:

- accepted certificate kinds;
- accepted verifier identities;
- accepted verification levels;
- required subject type;
- expiration sequence;
- exact subject and projection identity.

Mutating a constraint body, guard, provenance, evidence set, scope, or intended strength after certification breaks coverage.

## Certificates

A `CertificateRecord` identifies:

- the certified subject;
- the exact certificate payload;
- a deterministic payload fingerprint;
- the verifier expected to check it;
- scope and sequence provenance;
- status and verification linkage.

`ProjectionCertificateVerifier` independently reconstructs the intended hard-constraint projection and checks exact semantic coverage. `DetachedDigestVerifier` checks detached artifacts by SHA-256.

A certificate can prove that a particular object matches what was checked. It cannot prove that an external measurement, simulation, legal interpretation, or domain theory is true unless an appropriate domain verifier establishes that fact.

## Durable-history replay verification

`check_history()` does not merely inspect the final snapshot. It replays the authoritative event stream through the reducer and compares the reconstructed machine with persisted state.

The report checks:

- contiguous and monotonic event sequence;
- unique event identities and positive schema versions;
- single-machine history;
- state continuity and legal transitions;
- terminal-state absorption;
- exact reconstructed-versus-persisted snapshot equality;
- calculus invariants;
- active-lock validity;
- profile-binding fingerprint integrity;
- safe completion with no unresolved mandatory persistent obligations;
- certificate policy for every active hard constraint;
- preservation of hard-constraint records across replay.

Reports are `PASS`, `FAIL`, or `INCONCLUSIVE` and contain structured issue codes, sequence locations, hashes, and replay boundaries.

When a history report is persisted, the report records the event boundary it checked. The event used to store the report is intentionally outside that checked boundary.

## Conflict-core minimization

`minimize_conflict_core()` supports:

- `NONE`;
- `GREEDY_IRREDUCIBLE`;
- `EXACT_BOUNDED`.

Before claiming a minimized core, AASM verifies that the complete supplied literal set actually reproduces the conflict. Duplicate literals are canonicalized. Exact mode includes the empty subset, so an unconditional root conflict can be identified correctly.

A root conflict is not adopted as a no-good explanation because an empty body has different semantics from an assumption-dependent exclusion.

When a minimized core is adopted, AASM creates a successor explanation with a new identity and provenance link. The original explanation is not rewritten. Constraints and certificates already derived from the original therefore retain an immutable subject.

## Bounded formal models

The TLA+ and Promela/SPIN models separate these transitions:

```text
learn soft
register certificate
verify certificate
promote hard
```

They also model candidate staging and one-step atomic activation, restart preservation, terminal safety, and bounded fairness progress.

Formal CI runs whenever a transition-critical runtime file changes. It downloads pinned tool versions, verifies their SHA-256 hashes, executes TLC, builds SPIN, and runs the generated verifier including the fairness property.


### Hierarchical-scope model

v0.31.0 adds:

```text
formal/AASMScopeHierarchy.tla
formal/AASMScopeHierarchy.cfg
formal/aasm_scope_hierarchy.pml
```

The bounded models check root and strategy authority retention, pinned-parent and certified-hard-knowledge retention, local override isolation, causal invalidation of one branch, sibling preservation, and scoped restart preserving parents and siblings.

These are bounded abstractions of selected control properties. They are not a proof that arbitrary adapters, external tools, domain evidence, or every line of the Python runtime is correct.

## Correctness boundary

AASM distinguishes two questions:

1. **Machine authority:** Is this object allowed to influence durable machine behavior under the configured policy?
2. **Domain truth:** Is the underlying claim actually correct in the real world?

AASM substantially strengthens the first. The second remains the responsibility of domain-specific validation, trusted evidence sources, and appropriate human or technical review.
