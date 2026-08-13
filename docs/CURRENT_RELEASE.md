# AASM v0.37.0 — Reasoning Artifacts and Epistemic Admission

v0.37.0 adds durable typed reasoning artifacts and policy-governed epistemic admission over the v0.36 semantic compiler.

## Contracts

```text
aasm.reasoning.artifact.v1  / 0.1.0
aasm.reasoning.admission.v1 / 0.1.0
aasm.reasoning.commit.v1    / 0.1.0
aasm.semantic.compiler.v1   / 0.1.0
aasm.semantic.problem.v1    / 0.1.0
```

## Artifact types

```text
Claim
Hypothesis
Lemma
Invariant
Counterexample
Definition
Assumption
Observation
Derivation
Refutation
ObjectiveResult
```

## Epistemic lifecycle

```text
PROPOSED
SUPPORTED
CONTESTED
VERIFICATION_REQUESTED
VERIFIED
AUTHORIZED
REFUTED
STALE
REJECTED
```

## Delivered

- deterministic artifact IDs and fingerprints;
- producer authority classes and explicit verifier requirements;
- `propose_artifact`, `support_artifact`, `contest_artifact`, `request_verification`, `record_verification`, `authorize_artifact`, `refute_artifact`, `mark_stale`, and `reject_artifact`;
- `ReasoningCommit` over authorized artifacts only;
- independent verification with self-verification rejection;
- evidence existence checks and source-linked transition provenance;
- policy/controller authorization gates;
- append-only reasoning transitions represented through ordinary AASM Evidence;
- deterministic reasoning projection and replay/restart preservation;
- direct/forged reasoning record detection;
- Python, CLI, inspection, JSON-schema, and conformance surfaces;
- dependency propagation explicitly deferred to v0.38.

```text
package/runtime: 0.37.0
adoption:         aasm.adoption.v1 / 0.13.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.38.0 Semantic Dependency Graph and Truth Maintenance
```
