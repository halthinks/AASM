# Formal Assurance

AASM v0.24 adds an assurance layer over the conflict-learning calculus. The objective is not to make every domain claim mathematically true; it is to make the process by which machine knowledge becomes authoritative explicit, durable, independently checkable, and replayable.

## Certificates

A `CertificateRecord` identifies:

- the subject being certified;
- the exact certificate payload;
- a deterministic payload fingerprint;
- the verifier that is expected to check it;
- scope and sequence provenance;
- verification status.

`ProjectionCertificateVerifier` independently reconstructs the intended hard learned-constraint projection and verifies exact semantic coverage. `DetachedDigestVerifier` verifies arbitrary detached artifacts by SHA-256.

## Certificate-gated hard knowledge

The recommended lifecycle is:

```text
conflict
  -> validated explanation
  -> SOFT learned constraint
  -> certificate
  -> independent verification
  -> explicit HARD promotion
```

The runtime rechecks that a verified certificate still covers the current constraint before hard promotion. Mutating a body, guard, provenance, or scope after certification invalidates that coverage.

## Durable-history checking

`check_history()` evaluates properties of the persisted event history and reconstructed snapshot, including:

- monotonic event sequence;
- unique event IDs;
- single-machine history;
- absorbing terminal-state behavior;
- safe completion with no unresolved mandatory persistent obligations.

Reports are `PASS`, `FAIL`, or `INCONCLUSIVE` and contain structured issues.

## Conflict-core minimization

`minimize_conflict_core()` supports:

- `NONE`;
- `GREEDY_IRREDUCIBLE`;
- `EXACT_BOUNDED`.

Minimization is driven through a `ConflictOracle`. A literal is removed only when the oracle establishes that the reduced assumption set still reproduces the conflict. Exact mode reports `PROVEN_MINIMAL` only when its declared search finishes within budget.

## Correctness boundary

AASM can prove that a certificate covers a particular machine object or that an artifact has a particular digest. It does not automatically prove that a simulator is physically accurate, a measurement is honest, or a domain theory is complete. Domain truth and machine authority remain deliberately separate.
