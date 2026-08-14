# AASM v0.42.0 — Reference Domains & Reuse/Memory/Reasoning Stress Tests

AASM v0.42 is a reference-harness and public-surface release over the existing domain-neutral v0.41 solver runtime. It does not introduce `runtime_v42.py`, a second scheduler, a second reducer, or domain-specific truth logic. The active engine remains `runtime_v41.AASMEngine`; v0.42 tests that engine across materially different problem classes.

Contracts:

```text
aasm.adoption.v1 / 0.18.0
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.semantic.dependencies.v1 / 0.1.0
aasm.reasoning.admission.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## Reference domains

The deterministic offline harness executes five domains:

1. **constraint-solving** — exact subproblem reuse, hot-index deletion, environment invalidation, and certificate-gated solver skipping;
2. **software-repair** — freshness, dependency changes, and non-idempotent effect safety;
3. **research-synthesis** — authorized Reasoning Artifact reuse followed by truth-status invalidation;
4. **formal-reasoning** — explicit verification-strength requirements and reuse of adequately verified formal results;
5. **long-horizon-memory** — principal privacy, governed memory use, and tombstone/revocation invalidation.

Every reference scenario also asserts that replay reconstructs the same canonical machine state.

## Strengthened reuse boundary

v0.42 closes a stress-discovered gap: `ReuseRequest.required_strength` is now independently checked against the candidate's `verification_strength`. Matching a request fingerprint is not sufficient to bypass the requested assurance strength. A mismatch is rejected as `verification_strength_mismatch`.

The runtime does not invent a total order among strength labels. If a caller wants one verification class to satisfy another, that relationship must be made an explicit contract rather than an implicit string ranking.

## Correctness boundary

The v0.42 harness is synthetic, deterministic, and offline. It verifies architecture invariants and cross-layer behavior; it does not claim that arbitrary domain models, research conclusions, software diagnoses, mathematical statements, or memories are true. It requires no production adapter, model key, network access, or external solver.

Semantic/adversarial certification of arbitrary domain packages remains outside this release. That is the planned v0.43 boundary.

Release identity:

```text
package/runtime surface: 0.42.0
kernel engine: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.18.0
reference domains: aasm.reference-domains.v1 / 0.1.0
remote: aasm.remote.v1 / 0.19.0
next: v0.43.0 Semantic Conformance, Adversarial Domains, and Certification
```
